import sentry_sdk
import old_producer.main as old_producer
import old_worker.main as old_worker
import os
import dotenv
import utils.path as path
import asyncio

sentry_sdk.init(
    dsn="https://c80fe5043d5f19b11fa4f5106e5d2651@o4507149535936512.ingest.us.sentry.io/4508338032541696",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for tracing.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
    
    environment="development"
)

dotenv.load_dotenv(path.findFile(".env"),
                   override=True)

starts : dict = {
    "producer" : old_producer.start,
    "worker" : old_worker.start
}

def main():
    try:
        mode = os.environ.get("MODE").lower()
        
        print(f"Starting {mode}...")
        
        starts[mode]()
    except KeyboardInterrupt:
        try:
            print("OS Exiting...")
            os._exit(0)
        except:  # noqa: E722
            import sys
            print("System Exiting...")
            sys.exit(0)
    
if __name__ == "__main__":
    main()