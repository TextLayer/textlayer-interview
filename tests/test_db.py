import pytest
from app import create_app  

@pytest.fixture
def client():
    app = create_app('TEST')
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def post_query(client, query):
    response = client.post(
        "/v1/threads/chat",
        json={"messages": [{"role": "user", "content": query}]}
    )
    print(f"Request query: {query}")
    print(f"Status code: {response.status_code}")
    try:
        print("Response JSON:", response.get_json())
    except Exception:
        print("Response data (raw):", response.data.decode())
    return response



def test_ask_time_periods(client):
    response = post_query(client, "What are the available time periods in the dataset?")
    assert response.status_code == 200
    assert "YTD" in response.json.get("content", "") or "Q1" in response.json.get("content", "")


def test_list_customers(client):
    response = post_query(client, "List all customers.")
    assert response.status_code == 200
    assert any(keyword in response.json.get("content", "").lower() for keyword in ["customer", "west", "midwest"])


def test_account_metrics(client):
    response = post_query(client, "What are the metrics for account C1000?")
    assert response.status_code == 200
    assert "C1000" in response.json.get("content", "") or "West" in response.json.get("content", "")


def test_product_breakdown(client):
    response = post_query(client, "Show product breakdown by category.")
    assert response.status_code == 200
    assert any(word in response.json.get("content", "").lower() for word in ["product", "category", "breakdown"])


def test_ytd_time_perspective(client):
    response = post_query(client, "Give me YTD sales data.")
    assert response.status_code == 200
    assert "YTD" in response.json.get("content", "") or "sales" in response.json.get("content", "")


def test_version_info(client):
    response = post_query(client, "What is the current dataset version?")
    assert response.status_code == 200
    assert "version" in response.json.get("content", "").lower()


def test_customer_industry_grouping(client):
    response = post_query(client, "Group customers by industry.")
    assert response.status_code == 200
    assert any(word in response.json.get("content", "").lower() for word in ["industry", "customer", "group"])


def test_invalid_query(client):
    response = post_query(client, "asdkjl123##@!")
    assert response.status_code == 200
    assert "couldn't understand" in response.json.get("content", "").lower() or len(response.json.get("content", "")) < 100

