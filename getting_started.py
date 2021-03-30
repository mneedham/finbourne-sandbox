import lusid
import lusid.models as models
from lusid.utilities import ApiConfigurationLoader

import uuid
import datetime
import pytz

secrets_file_path = "/Users/markneedham/projects/lusid-sdk-java-preview/sdk/src/test/resources/secrets.json"
config = ApiConfigurationLoader.load(secrets_file_path)
api_factory = lusid.utilities.ApiClientFactory(
    token=lusid.utilities.RefreshingToken(config),
    api_secrets_filename=secrets_file_path
)
api_client = api_factory.api_client
instruments_api = api_factory.build(lusid.api.InstrumentsApi)
tx_portfolios_api = api_factory.build(lusid.api.TransactionPortfoliosApi)

# Create a portfolio

# You need to set the timezone or it will throw an error
portfolio_creation_date = datetime.datetime(2021, 3, 20, tzinfo=pytz.utc)
scope = "GettingStartedScope"
guid = uuid.uuid4()

portfolio_request = models.CreateTransactionPortfolioRequest(
    display_name=f"Portfolio-{guid}",
    code=f"Id-{guid}",
    base_currency="GBP",
    created=portfolio_creation_date
)

portfolio = tx_portfolios_api.create_portfolio(scope, create_transaction_portfolio_request=portfolio_request)
portfolio_code = portfolio.id.code
print("portfolio:", portfolio_code)

# Add instruments
# FIGIs are from https://www.openfigi.com/search#!?page=1
figis_to_create = {
    figi: models.InstrumentDefinition(
        name=name,
        identifiers={"Figi": models.InstrumentIdValue(value=figi)}
    ) for figi, name in [("BBG000C6K6G9", "VODAFONE GROUP PLC"), ("BBG000C04D57", "BARCLAYS PLC")]
}

instruments_api.upsert_instruments(request_body=figis_to_create)

instruments = {
    value.name: value.lusid_instrument_id
    for _, value in instruments_api.get_instruments(identifier_type="Figi",
                                                    request_body=list(figis_to_create.keys())).values.items()
}
inverted_instruments = {v: k for k, v in instruments.items()}

# Add transactions
vodafone_id = instruments["VODAFONE GROUP PLC"]
tx1 = models.TransactionRequest(
    transaction_id=f"Transaction-{uuid.uuid4()}",
    type="StockIn",
    instrument_identifiers={"Instrument/default/LusidInstrumentId": vodafone_id},
    transaction_date=datetime.datetime(2021, 3, 27, tzinfo=pytz.utc),
    settlement_date=datetime.datetime(2021, 3, 28, tzinfo=pytz.utc),
    units=100,
    transaction_price=models.TransactionPrice(price=103),
    total_consideration=models.CurrencyAndAmount(amount=103 * 100, currency="GBP"),
    source="Broker"
)
tx2 = models.TransactionRequest(
    transaction_id=f"Transaction-{uuid.uuid4()}",
    type="StockIn",
    instrument_identifiers={"Instrument/default/LusidInstrumentId": vodafone_id},
    transaction_date=datetime.datetime(2021, 3, 29, tzinfo=pytz.utc),
    settlement_date=datetime.datetime(2021, 3, 29, tzinfo=pytz.utc),
    units=500,
    transaction_price=models.TransactionPrice(price=98),
    total_consideration=models.CurrencyAndAmount(amount=98 * 500, currency="GBP"),
    source="Broker"
)

tx_portfolios_api.upsert_transactions(scope=scope, code=portfolio_code, transaction_request=[tx1, tx2])

# Get transactions
transactions = tx_portfolios_api.get_transactions(scope=scope, code=portfolio_code)
print("Transactions:")
for transaction in transactions.values:
    print(inverted_instruments[transaction.instrument_uid],
          f"{transaction.units} units @ {transaction.transaction_price.price}")

# Get holdings
holdings_response = tx_portfolios_api.get_holdings(scope=scope, code=portfolio_code,
                                                   property_keys=["Instrument/default/Name"]).values

print("Holdings:")
for holding in holdings_response:
    print(inverted_instruments[holding.instrument_uid], holding.units, holding.cost.amount)
