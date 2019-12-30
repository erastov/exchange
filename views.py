import json

from aiohttp import web
from settings import CURRENCIES

routes = web.RouteTableDef()


def get_param(request, name_param, error_message=None):
    param = request.rel_url.query.get(name_param)

    if not param:
        error_message = (
            error_message if error_message else f"Not found query param: `{name_param}`"
        )
        raise web.HTTPBadRequest(body=json.dumps({"error": error_message}))
    return param


def validate_exchange_rates(data):
    current_currencies = set()
    for key in data:
        try:
            from_currency, to_currency = key.split("_")
        except ValueError:
            raise web.HTTPBadRequest(body=json.dumps({"error": f"Not valid currencies name: {key}"}))
        else:
            current_currencies.add(from_currency)
            current_currencies.add(to_currency)

    diff = current_currencies - CURRENCIES
    if diff:
        raise web.HTTPBadRequest(body=json.dumps({"error": f"Not valid currencies: {', '.join(diff)}"}))


@routes.get("/convert")
async def convert(request):
    from_currency = get_param(
        request, "from", "Required param: `from` (ex: RUR)"
    ).lower()
    to_currency = get_param(request, "to", "Required param: `to` (ex: USD)").lower()
    amount = int(
        get_param(request, "amount", "Required param: `amount` (must be integer)")
    )

    val = await request.app["redis_pool"].get(f"{from_currency}_{to_currency}")
    inverse_val = await request.app["redis_pool"].get(f"{to_currency}_{from_currency}")

    if not val and not inverse_val:
        raise web.HTTPBadRequest(
            body=json.dumps({"error": "Not found `to` or `from` currency"})
        )

    result = amount * int(val) if val else amount * (1 / int(inverse_val))

    return web.Response(body=json.dumps({"result": result}))


@routes.post("/database")
async def database(request):
    merge = int(get_param(request, "merge", "Required param: `merge` (must be 0 or 1)"))
    data = await request.json()

    validate_exchange_rates(data)

    if merge not in (0, 1):
        raise web.HTTPBadRequest(
            body=json.dumps({"error": "Not valid `merge` param (must be 0 or 1)"})
        )

    transaction = request.app["redis_pool"].multi_exec()

    if merge == 0:
        transaction.flushall()

    transaction.mset(data)
    result = await transaction.execute()

    if all(result):
        return web.Response(body=json.dumps({"result": "Successfully updated"}))
    else:
        raise web.HTTPInternalServerError(text="Oops, some error. Try again.")
