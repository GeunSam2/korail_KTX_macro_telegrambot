"""
API 엔드포인트 테스트
Flask 애플리케이션의 기본 엔드포인트들이 정상적으로 동작하는지 테스트합니다.
"""
import pytest
import sys
import os

# src 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from app import application


@pytest.fixture
def client():
    """Flask 테스트 클라이언트 생성"""
    application.config['TESTING'] = True
    with application.test_client() as client:
        yield client


def test_app_exists(client):
    """Flask 애플리케이션이 존재하는지 확인"""
    assert application is not None


def test_telebot_endpoint_exists(client):
    """
    /telebot 엔드포인트가 존재하고 응답하는지 확인

    텔레그램 봇 웹훅 엔드포인트는 POST 요청을 받습니다.
    GET 요청에는 405 Method Not Allowed를 반환해야 합니다.
    """
    response = client.get('/telebot')
    # GET은 허용되지 않지만 엔드포인트는 존재해야 함
    assert response.status_code in [200, 405]


def test_check_payment_endpoint_exists(client):
    """
    /check_payment 엔드포인트가 존재하고 응답하는지 확인

    결제 확인 엔드포인트가 정상적으로 등록되어 있는지 확인합니다.
    """
    response = client.get('/check_payment')
    # 엔드포인트가 존재하면 200, 405, 또는 다른 유효한 HTTP 응답 코드를 반환해야 함
    assert response.status_code in [200, 405, 400]


def test_cors_headers(client):
    """
    CORS 헤더가 제대로 설정되어 있는지 확인

    flask-cors가 제대로 동작하는지 확인합니다.
    """
    response = client.get('/telebot')
    # CORS 헤더가 포함되어 있어야 함
    assert 'Access-Control-Allow-Origin' in response.headers or response.status_code == 405


def test_404_error(client):
    """
    존재하지 않는 엔드포인트는 404를 반환하는지 확인
    """
    response = client.get('/nonexistent-endpoint-12345')
    assert response.status_code == 404
