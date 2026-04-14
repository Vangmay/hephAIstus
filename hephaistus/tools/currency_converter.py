
import requests

def convert_currency(amount: float, from_currency: str, to_currency: str) -> float:
    """
    Converts a given amount from one currency to another using real-time exchange rates.

    :param amount: The amount to convert.
    :param from_currency: The currency to convert from (e.g., 'USD').
    :param to_currency: The currency to convert to (e.g., 'EUR').
    :return: The converted amount.
    """
    api_key = 'YOUR_API_KEY'  # Replace with your actual API key
    base_url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"

    try:
        response = requests.get(base_url)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        exchange_rate = data['rates'][to_currency]
        return amount * exchange_rate
    except requests.exceptions.RequestException as e:
        print(f"Error fetching exchange rates: {e}")
        return None
    except KeyError:
        print(f"Invalid currency: {to_currency}")
        return None

if __name__ == '__main__':
    # Example usage:
    converted_amount = convert_currency(100, 'USD', 'EUR')
    if converted_amount is not None:
        print(f"100 USD is equal to {converted_amount:.2f} EUR")
