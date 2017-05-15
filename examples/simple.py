import asyncio
import faust
import io
import os
import sys

GRAPH = os.environ.get('GRAPH')


class Withdrawal(faust.Record, serializer='json'):
    user: str
    country: str
    amount: float


app = faust.App(
    'f-simple',
    url='kafka://localhost:9092',
)
withdrawals_topic = app.topic('withdrawals', value_type=Withdrawal)


@app.actor(withdrawals_topic)
async def find_large_withdrawals(withdrawals):
    user_to_total = app.table('user_to_total', default=int)
    country_to_total = app.table('country_to_total', default=int)
    async for withdrawal in withdrawals:
        user_to_total[withdrawal.user] += withdrawal.amount
        country_to_total[withdrawal.country] += withdrawal.amount
        print('Withdrawal: %r, User Total: %r, Country Total: %r' % (
            withdrawal, user_to_total[withdrawal.user],
            country_to_total[withdrawal.country]))


async def _dump_beacon(app):
    await asyncio.sleep(4)
    print(app.render_graph())


async def _publish_withdrawals():
    for i in range(10_000):
        print('+SEND %r' % (i,))
        await withdrawals_topic.send(
            b'K', Withdrawal(user='foo', amount=100.3 + i, country='FOO'))
        print('-SEND %r' % (i,))
    await withdrawals_topic.send(
            b'K', Withdrawal(user='foo', amount=999999.0, country='BAR'))
    await asyncio.sleep(30)


def produce(loop):
    loop.run_until_complete(_publish_withdrawals())


COMMANDS = {
    'consume': app.start,
    'produce': produce,
}


def main(loop=None):
    loop = loop or asyncio.get_event_loop()
    try:
        command = sys.argv.pop(1)
    except KeyError as exc:
        print('Unknown command: {0}'.format(exc))
        raise SystemExit(os.EX_USAGE)
    except IndexError:
        print('Missing command. Try one of: {0}'.format(', '.join(COMMANDS)))
        raise SystemExit(os.EX_USAGE)
    else:
        COMMANDS[command](loop=loop)
    finally:
        loop.close()


if __name__ == '__main__':
    main()
