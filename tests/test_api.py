from fastapi.testclient import TestClient

from app.main import app


def test_health_responde_200():
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_pagina_inicial_responde_html():
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "DeckValor" in response.text


def test_api_retorna_informacoes():
    response = TestClient(app).get("/api")

    assert response.status_code == 200
    assert response.json()["documentacao"] == "/docs"
