import pytest
from requests import HTTPError, Timeout
from rynaki import Akinator, AkinatorError


class FakeResponse:
    def __init__(self, payload=None, text="", error=None):
        self.payload = payload
        self.text = text
        self.error = error

    def raise_for_status(self):
        if self.error is not None:
            raise self.error

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class FakeScraper:
    def __init__(self, payload=None, text="", error=None):
        self.payload = payload
        self.text = text
        self.error = error
        self.calls = []

    def post(self, url, data, timeout):
        self.calls.append((url, dict(data), timeout))
        return FakeResponse(self.payload, self.text, self.error)


CURRENT_GAME_HTML = """
<input id="session" name="session">
<div id="question-label">First question?</div>
<form id="askSoundlike">
    <input id="session" name="session" value="test-session">
</form>
<script>
localStorage.setItem('step', '1');
localStorage.setItem('progression', '0');
</script>
"""

LEGACY_GAME_HTML = """
<div id="question-label">First question?</div>
<form id="askSoundlike">
    <input id="session" name="session" value="legacy-session">
    <input id="signature" name="signature" value="legacy-signature">
</form>
"""


def current_game():
    akinator = Akinator(lang="cn")
    akinator.scraper = FakeScraper(text=CURRENT_GAME_HTML)
    akinator.start_game()
    return akinator


def test_post_answer_accepts_question_without_akitude():
    akinator = Akinator(lang="en")
    akinator.json.update({"session": "session", "signature": "signature"})
    akinator.scraper = FakeScraper({
        "completion": "OK",
        "step": "1",
        "progression": "12.9372",
        "question_id": "8617",
        "question": "Is your character a singer?",
    })

    response = akinator.post_answer("y")

    assert response["question"] == "Is your character a singer?"
    assert akinator.question == "Is your character a singer?"
    assert akinator.step == 1
    assert akinator.progression == 12.9372
    assert akinator.akitude == "https://en.akinator.com/assets/img/akitudes_670x1096/defi.png"
    assert akinator.json["question_id"] == "8617"


def test_start_game_without_signature_reads_initial_state_and_posts_form_data():
    akinator = current_game()

    assert akinator.question == "First question?"
    assert akinator.json["session"] == "test-session"
    assert "signature" not in akinator.json
    assert akinator.step == akinator.json["step"] == 1
    assert akinator.progression == akinator.json["progression"] == 0.0
    assert akinator.scraper.calls == [
        ("https://cn.akinator.com/game", {"sid": 1, "cm": "false"}, 20),
    ]


def test_legacy_signature_and_state_are_reset_when_starting_another_game():
    akinator = Akinator(lang="cn")
    akinator.scraper = FakeScraper(text=LEGACY_GAME_HTML)
    akinator.start_game()
    assert akinator.json["signature"] == "legacy-signature"
    assert akinator.step == 0
    akinator.json.update({"question_id": "old-question", "step_last_proposition": 15})
    akinator.name = "Previous guess"

    akinator.scraper.text = CURRENT_GAME_HTML
    akinator.start_game()
    assert "signature" not in akinator.json
    assert "question_id" not in akinator.json
    assert "step_last_proposition" not in akinator.json
    assert akinator.name is None
    assert akinator.question_id is None
    assert akinator.step == 1


def test_session_outside_soundlike_form_is_supported():
    akinator = Akinator()
    akinator.scraper = FakeScraper(text=CURRENT_GAME_HTML.replace('id="askSoundlike"', 'id="other-form"'))
    akinator.start_game()
    assert akinator.json["session"] == "test-session"


@pytest.mark.parametrize("html", [
    "<html>Service unavailable</html>",
    '<div id="question-label">Question?</div>',
    '<input name="session" value="test-session">',
    CURRENT_GAME_HTML.replace('value="test-session"', 'value=""'),
    CURRENT_GAME_HTML.replace('First question?', ' '),
])
def test_missing_question_or_session_raises_akinator_error(html):
    akinator = Akinator()
    akinator.scraper = FakeScraper(text=html)
    with pytest.raises(AkinatorError):
        akinator.start_game()


def test_initial_progression_and_numeric_storage_values_are_read():
    akinator = Akinator()
    akinator.scraper = FakeScraper(text=CURRENT_GAME_HTML.replace("'1'", "1").replace("'0'", "12.5"))
    akinator.start_game()
    assert akinator.step == 1
    assert akinator.progression == 12.5


@pytest.mark.parametrize("error", [HTTPError(), Timeout()])
def test_start_game_http_errors_raise_akinator_error(error):
    akinator = Akinator()
    akinator.scraper = FakeScraper(text=CURRENT_GAME_HTML, error=error)
    with pytest.raises(AkinatorError):
        akinator.start_game()


def test_answer_uses_initial_state_and_advances_without_akitude():
    akinator = current_game()
    akinator.scraper.payload = {
        "completion": "OK", "question": "Next?", "step": "2", "progression": "12.5",
    }
    akinator.post_answer("pn")

    assert akinator.question == "Next?"
    assert akinator.step == akinator.json["step"] == 2
    assert akinator.progression == akinator.json["progression"] == 12.5
    assert akinator.scraper.calls[-1] == (
        "https://cn.akinator.com/answer",
        {"sid": 1, "cm": "false", "answer": 4, "session": "test-session", "step": 1, "progression": 0.0},
        20,
    )


@pytest.mark.parametrize("answer,answer_id", [("y", 0), ("n", 1), ("idk", 2), ("p", 3), ("pn", 4)])
def test_answer_mapping(answer, answer_id):
    akinator = current_game()
    akinator.scraper.payload = {"question": "Next?", "step": 2, "progression": 5}
    akinator.post_answer(answer)
    assert akinator.scraper.calls[-1][1]["answer"] == answer_id


def test_invalid_answer_does_not_send_a_request():
    akinator = current_game()
    with pytest.raises(AkinatorError):
        akinator.post_answer("invalid")
    assert len(akinator.scraper.calls) == 1


def test_guess_without_optional_description_or_photo_finishes():
    akinator = current_game()
    akinator.scraper.payload = {"completion": "OK", "name_proposition": "A character", "id_proposition": "123"}
    akinator.post_answer("y")
    assert akinator.name == "A character"
    assert akinator.description == ""
    assert akinator.photo is None


@pytest.mark.parametrize("payload", [
    None, [], {}, ValueError(), {"completion": "KO"}, {"completion": "SOUNDLIKE"},
    {"question": "Next?"}, {"question": "Next?", "step": None, "progression": 0},
])
def test_invalid_answer_responses_raise_akinator_error(payload):
    akinator = current_game()
    akinator.scraper.payload = payload
    with pytest.raises(AkinatorError):
        akinator.post_answer("y")


def test_cannot_go_back_from_the_current_sites_first_step():
    akinator = current_game()
    with pytest.raises(AkinatorError):
        akinator.go_back()
    assert len(akinator.scraper.calls) == 1


def test_go_back_uses_form_data_and_restores_first_question():
    akinator = current_game()
    akinator.scraper.payload = {"question": "Next?", "step": 2, "progression": 12.5}
    akinator.post_answer("y")
    akinator.scraper.payload = {"question": "First question?", "step": 1, "progression": 0}
    akinator.go_back()
    assert akinator.step == 1
    assert akinator.scraper.calls[-1] == (
        "https://cn.akinator.com/cancel_answer",
        {"sid": 1, "cm": "false", "session": "test-session", "step": 2, "progression": 12.5},
        20,
    )


def test_exclude_uses_form_data_and_keeps_question_id():
    akinator = current_game()
    akinator.scraper.payload = {"question": "Next?", "step": 2, "progression": 12.5, "question_id": "321"}
    akinator.exclude()
    assert akinator.question_id == "321"
    assert akinator.scraper.calls[-1][0] == "https://cn.akinator.com/exclude"


@pytest.mark.parametrize("method", ["go_back", "exclude"])
@pytest.mark.parametrize("payload", [None, [], ValueError()])
def test_other_endpoints_reject_invalid_json(method, payload):
    akinator = current_game()
    akinator.json["step"] = 2
    akinator.scraper.payload = payload
    with pytest.raises(AkinatorError):
        getattr(akinator, method)()
