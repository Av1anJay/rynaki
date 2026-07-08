from rynaki import Akinator


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class FakeScraper:
    def __init__(self, payload):
        self.payload = payload

    def post(self, url, json):
        return FakeResponse(self.payload)


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
