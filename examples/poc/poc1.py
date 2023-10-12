import asyncio
from broqer import Value, op, Sink
v = Value()
throttle_publisher = v | op.Throttle(0.1)
_d = throttle_publisher.subscribe(Sink(print))
v.emit(1)

v.emit(2)
asyncio.get_event_loop().run_until_complete(asyncio.sleep(0.05))
v.emit(3)
asyncio.get_event_loop().run_until_complete(asyncio.sleep(0.2))

# It's also possible to reset the throttling duration:
v.emit(4)

v.emit(5)
asyncio.get_event_loop().run_until_complete(asyncio.sleep(0.05))
throttle_publisher.reset()