import asyncio

from memory.extraction_queue import ExtractionQueue
from memory.memory_extractor import MemoryExtractor


class MemoryQueueWorker:

    def __init__(self, memory_manager, interval=30):

        self.queue = ExtractionQueue()

        self.extractor = MemoryExtractor(memory_manager)

        self.interval = max(5, interval)

        self.running = False

        self.stop_event = asyncio.Event()

    async def process_pending(self):

        pending_tasks = self.queue.get_pending(limit=5)

        for task in pending_tasks:

            if not self.running:
                break

            queue_id = task["id"]

            conversation = task["conversation"]

            try:

                claimed = self.queue.mark_processing(queue_id)

                if not claimed:
                    continue

                print(
                    f"\nZORIN MEMORY WORKER: "
                    f"Processing task {queue_id}..."
                )

                memories = await self.extractor.extract(
                    conversation
                )

                if memories is None:

                    self.queue.mark_pending(queue_id)

                    print(
                        f"Task {queue_id} returned to pending queue."
                    )

                    continue

                self.queue.mark_completed(queue_id)

                print(
                    f"ZORIN MEMORY WORKER: "
                    f"Task {queue_id} completed. "
                    f"{len(memories)} memories saved."
                )

            except asyncio.CancelledError:

                try:
                    self.queue.mark_pending(queue_id)

                except Exception as error:
                    print("QUEUE RECOVERY ERROR:", repr(error))

                raise

            except Exception as error:

                try:
                    self.queue.mark_pending(queue_id)

                except Exception as recovery_error:
                    print(
                        "QUEUE RECOVERY ERROR:",
                        repr(recovery_error)
                    )

                print(
                    "\nZORIN MEMORY WORKER ERROR:",
                    repr(error)
                )

    async def run(self):

        if self.running:
            return

        self.running = True

        self.stop_event.clear()

        recovered = self.queue.recover_processing()

        if recovered:

            print(
                f"\nZORIN MEMORY: "
                f"Recovered {recovered} unfinished tasks."
            )

        print("\nZORIN BACKGROUND MEMORY WORKER STARTED.")

        try:

            while self.running:

                try:

                    await self.process_pending()

                except asyncio.CancelledError:
                    raise

                except Exception as error:

                    print(
                        "\nMEMORY WORKER ERROR:",
                        repr(error)
                    )

                if not self.running:
                    break

                try:

                    await asyncio.wait_for(
                        self.stop_event.wait(),
                        timeout=self.interval
                    )

                except asyncio.TimeoutError:
                    pass

        finally:

            self.running = False

            print(
                "\nZORIN BACKGROUND MEMORY WORKER STOPPED."
            )

    def stop(self):

        self.running = False

        self.stop_event.set()