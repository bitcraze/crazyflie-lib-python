import asyncio
import math
import time
from cflib import Crazyflie, LinkContext


def fly_one(cf: Crazyflie) -> None:
    """Blocking flight routine for one Crazyflie."""
    print(f"[{cf}] Starting sequence")
    # hlc = cf.high_level_commander()
    param = cf.param()
    param_name = "led.bitmask"

    try:
        for _ in range(10):
            param.set(param_name, 212)
            time.sleep(2)
            param.set(param_name, 0)
            time.sleep(2)
    finally:
        # hlc.stop(None)
        cf.disconnect()
        print(f"[{cf}] Done")


async def main() -> None:
    context = LinkContext()
    uris = [
        "radio://0/30/2M/BADC0DE007",
        "radio://0/30/2M/BADBADBAD4",
        "radio://0/30/2M/BADBADBAD5",
        "radio://0/30/2M/BADC0DE016",
    ]

    # Connect all drones concurrently in threads
    cfs = await asyncio.gather(
        *[asyncio.to_thread(Crazyflie.connect_from_uri, context, uri) for uri in uris]
    )

    # Run all flight sequences concurrently
    await asyncio.gather(*[asyncio.to_thread(fly_one, cf) for cf in cfs])


if __name__ == "__main__":
    asyncio.run(main())
