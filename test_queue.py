from memory.extraction_queue import ExtractionQueue

queue = ExtractionQueue()

test_text = "ZORIN offline queue verification test. This conversation must survive application restarts."

task_id = queue.enqueue(test_text)

assert task_id is not None, "FAILED: Could not enqueue task."

pending = queue.get_pending()

assert any(task["id"] == task_id for task in pending), "FAILED: Task not found."

queue.mark_processing(task_id)

recovered = queue.recover_processing()

pending = queue.get_pending()

assert any(task["id"] == task_id for task in pending), "FAILED: Crash recovery failed."

queue.mark_processing(task_id)
queue.mark_completed(task_id)

print("\nOFFLINE QUEUE TEST: SUCCESS")
print("Task ID:", task_id)
print("Crash recovery: SUCCESS")
print("Completion: SUCCESS")
print("Queue statistics:", queue.get_statistics())
