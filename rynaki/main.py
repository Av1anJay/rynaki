import cloudscraper
import re
from bs4 import BeautifulSoup
from requests import RequestException


DEFAULT_AKITUDE_URL = "https://en.akinator.com/assets/img/akitudes_670x1096/defi.png"


class AkinatorError(Exception):
    pass


class Akinator():
    def __init__(self, theme: str = "characters", lang: str = "ar", child_mode: bool = False) -> None:
        self.scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome',
                     'platform': 'windows', 'desktop': True}
        )
        self.scraper.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36'
        })
        
        self.ENDPOINT = f"https://{lang}.akinator.com/"
        self.name = None
        self.description = None
        self.photo = None
        self.answer_id = None
        self.akitude = DEFAULT_AKITUDE_URL
        self.question_id = None
        self._first_step = 0

        if theme == "characters":
            sid = 1
        elif theme == "objects":
            sid = 2
        elif theme == "animals":
            sid = 14
        else:
            raise AkinatorError(
                "Theme must be 'characters', 'objects', or 'animals'.")

        self.json = {
            "step": 0,
            "progression": 0.0,
            "sid": sid,
            "cm": child_mode,
            "answer": 0,
        }

    def _post(self, endpoint, payload):
        payload = dict(payload)
        if isinstance(payload.get("cm"), bool):
            payload["cm"] = "true" if payload["cm"] else "false"
        try:
            response = self.scraper.post(
                f"{self.ENDPOINT}{endpoint}", data=payload, timeout=20
            )
            response.raise_for_status()
            return response
        except RequestException as exc:
            raise AkinatorError("Akinator request failed.") from exc

    def _post_json(self, endpoint, payload):
        response = self._post(endpoint, payload)
        try:
            result = response.json()
        except ValueError as exc:
            raise AkinatorError("Invalid response received from Akinator API.") from exc
        if not isinstance(result, dict):
            raise AkinatorError("Invalid response received from Akinator API.")
        return result

    def start_game(self):
        self.name = None
        self.description = None
        self.photo = None
        self.answer_id = None
        self.question_id = None
        self.akitude = DEFAULT_AKITUDE_URL

        game = self._post("game", {
            "sid": self.json["sid"],
            "cm": self.json["cm"]
        }).text

        soup = BeautifulSoup(game, "html.parser")
        question_label = soup.find(id="question-label")
        session = soup.select_one("#askSoundlike input[name='session'][value]")
        if session is None:
            session = soup.select_one("input[name='session'][value]")
        if (question_label is None or not question_label.get_text(strip=True)
                or session is None or not session.get("value")):
            raise AkinatorError("Akinator did not return a valid game.")

        self.json = {
            "sid": self.json["sid"], "cm": self.json["cm"],
            "answer": 0, "session": session["value"],
        }
        # Signatures are absent on current pages but may exist on older ones.
        signature = soup.select_one("input[name='signature'][value]")
        if signature is not None and signature.get("value"):
            self.json["signature"] = signature["value"]

        # Current games start at step 1; older pages started at step 0.
        for key in ("step", "progression"):
            number = r"[0-9]+" if key == "step" else r"[0-9]+(?:\.[0-9]+)?"
            match = re.search(
                rf"localStorage\.setItem\(\s*['\"]{key}['\"]\s*,\s*"
                rf"['\"]?({number})['\"]?\s*\)",
                game,
            )
            value = match.group(1) if match else "0"
            self.json[key] = int(value) if key == "step" else float(value)
        self.step = self.json["step"]
        self._first_step = self.step
        self.progression = self.json["progression"]
        self.question = question_label.get_text(" ", strip=True)
        return self.question

    def post_answer(self, answer: str):
        answers_map = {"y": 0, "n": 1, "idk": 2, "p": 3, "pn": 4}
        if answer not in answers_map:
            raise AkinatorError(
                "Answer must be 'y', 'n', 'idk', 'p', or 'pn'.")

        self.json["answer"] = answers_map[answer]

        try:
            response = self._post_json("answer", self.json)

            if response.get("completion") == "KO":
                raise AkinatorError("Akinator session error (completion: KO). Please start a new game.")
            elif response.get("completion") == "SOUNDLIKE":
                raise AkinatorError("A 'sound like' guess was found, which is not supported.")

            if isinstance(response.get("question"), str) and response["question"].strip():
                self.json["step"] = int(response["step"])
                self.json["progression"] = float(response["progression"])
                if "question_id" in response:
                    self.json["question_id"] = response["question_id"]
                    self.question_id = response["question_id"]
                self.step = self.json["step"]
                self.progression = self.json["progression"]
                self.question = response["question"]
                if response.get("akitude"):
                    self.akitude = f"https://en.akinator.com/assets/img/akitudes_670x1096/{response['akitude']}"
            elif response.get("name_proposition"):
                self.name = response["name_proposition"]
                self.description = response.get("description_proposition", "")
                self.photo = response.get("photo")
                self.answer_id = response.get("id_proposition")
                self.json["step_last_proposition"] = int(self.json["step"])
            else:
                raise AkinatorError("Invalid response received from Akinator API.")
                
            return response
        except Exception as e:
            if isinstance(e, AkinatorError):
                raise e
            raise AkinatorError(f"Akinator request failed: {e}")

    def go_back(self):
        if self.json["step"] <= self._first_step:
            raise AkinatorError("It's the first question, can't go back.")

        self.name, self.description, self.photo, self.answer_id = None, None, None, None
        self.json.pop("answer", None)

        try:
            goback = self._post_json("cancel_answer", self.json)
            self.json["step"] = int(goback["step"])
            self.json["progression"] = float(goback["progression"])
            if "question_id" in goback:
                self.json["question_id"] = goback["question_id"]
                self.question_id = goback["question_id"]
            self.step = self.json["step"]
            self.progression = self.json["progression"]
            self.question = goback["question"]
            if goback.get("akitude"):
                self.akitude = f"https://en.akinator.com/assets/img/akitudes_670x1096/{goback['akitude']}"
            return goback
        except Exception as e:
            raise AkinatorError(f"Go back failed: {e}")

    def exclude(self):
        try:
            response = self._post_json("exclude", self.json)
        except Exception as e:
            raise AkinatorError(f"Exclude request failed: {e}")

        if response.get("completion") == "KO":
            raise AkinatorError("Exclude failed (completion: KO).")

        if "question" in response:
            self.json["step"] = int(response["step"])
            self.json["progression"] = float(response["progression"])
            if "question_id" in response:
                self.json["question_id"] = response["question_id"]
                self.question_id = response["question_id"]
            self.step = self.json["step"]
            self.progression = self.json["progression"]
            self.question = response["question"]
            if response.get("akitude"):
                self.akitude = f"https://en.akinator.com/assets/img/akitudes_670x1096/{response['akitude']}"
            self.name, self.description, self.photo, self.answer_id = None, None, None, None
        elif "name_proposition" in response:
            self.name = response["name_proposition"]
            self.description = response["description_proposition"]
            self.photo = response["photo"]
            self.answer_id = response["id_proposition"]
            self.json["step_last_proposition"] = int(self.json["step"])
        else:
            raise AkinatorError(f"Exclude failed to parse response.")
        
        return response
