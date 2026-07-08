import cloudscraper
from bs4 import BeautifulSoup


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

    def start_game(self):
        self.name = None
        self.description = None
        self.photo = None
        self.answer_id = None
        self.question_id = None
        self.akitude = DEFAULT_AKITUDE_URL

        game = self.scraper.post(f"{self.ENDPOINT}game", json={
            "sid": self.json["sid"],
            "cm": self.json["cm"]
        }).text

        soup = BeautifulSoup(game, "html.parser")
        askSoundlike = soup.find(id="askSoundlike")
        question_label = soup.find(id="question-label").get_text()
        session_id = askSoundlike.find(id="session").get("value")
        signature_id = askSoundlike.find(id="signature").get("value")

        self.json["session"] = session_id
        self.json["signature"] = signature_id
        self.step = 0
        self.progression = 0.0
        self.question = question_label
        self.question_id = None
        return self.question

    def post_answer(self, answer: str):
        answers_map = {"y": 0, "n": 1, "idk": 2, "p": 3, "pn": 4}
        if answer not in answers_map:
            raise AkinatorError(
                "Answer must be 'y', 'n', 'idk', 'p', or 'pn'.")

        self.json["answer"] = answers_map[answer]

        try:
            response = self.scraper.post(
                f"{self.ENDPOINT}answer", json=self.json).json()

            if response.get("completion") == "KO":
                raise AkinatorError("Akinator session error (completion: KO). Please start a new game.")
            elif response.get("completion") == "SOUNDLIKE":
                raise AkinatorError("A 'sound like' guess was found, which is not supported.")

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
            elif "name_proposition" in response:
                self.name = response["name_proposition"]
                self.description = response["description_proposition"]
                self.photo = response["photo"]
                self.answer_id = response["id_proposition"]
                self.json["step_last_proposition"] = int(self.json["step"])
            else:
                raise AkinatorError("Invalid response received from Akinator API.")
                
            return response
        except Exception as e:
            if isinstance(e, AkinatorError):
                raise e
            raise AkinatorError(f"Akinator request failed: {e}")

    def go_back(self):
        if self.json["step"] == 0:
            raise AkinatorError("It's the first question, can't go back.")

        self.name, self.description, self.photo, self.answer_id = None, None, None, None
        self.json.pop("answer", None)

        try:
            goback = self.scraper.post(
                f"{self.ENDPOINT}cancel_answer", json=self.json).json()
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
            response = self.scraper.post(
                f"{self.ENDPOINT}exclude", json=self.json
            ).json()
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
