import time
import threading
from collections import deque
import random


class TokenBucketRateLimiter:
    """
    A thread-safe token bucket rate limiter.
    """

    def __init__(self, max_tokens: int, refill_rate: float):
        """
        :param max_tokens: Maximum number of tokens the bucket can hold.
        :param refill_rate: Tokens added per second.
        """
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.available_tokens = max_tokens
        self.last_refill_timestamp = time.time()

        self.lock = threading.Lock()

    def _refill(self):
        now = time.time()
        elapsed = now - self.last_refill_timestamp

        refill_amount = elapsed * self.refill_rate
        if refill_amount > 0:
            self.available_tokens = min(self.max_tokens, self.available_tokens + refill_amount)
            self.last_refill_timestamp = now

    def allow_request(self) -> bool:
        """
        Attempt to consume a token.
        Returns True if request is allowed, False otherwise.
        """
        with self.lock:
            self._refill()

            if self.available_tokens >= 1:
                self.available_tokens -= 1
                return True
            else:
                return False


# ===========================
#  Simulation / Load Testing
# ===========================

class TrafficSimulator:
    def __init__(self, rate_limiter, num_threads=10, duration=5, load_profile="burst"):
        """
        :param rate_limiter: Instance of TokenBucketRateLimiter
        :param num_threads: Number of concurrent threads sending requests
        :param duration: Test duration in seconds
        :param load_profile: "burst" or "steady"
        """
        self.rate_limiter = rate_limiter
        self.num_threads = num_threads
        self.duration = duration
        self.load_profile = load_profile

        self.allowed = 0
        self.blocked = 0

        self.latencies = deque()
        self.lock = threading.Lock()

    def request_worker(self):
        """
        Worker thread simulating client traffic.
        """
        end_time = time.time() + self.duration

        while time.time() < end_time:
            start = time.time()

            allowed = self.rate_limiter.allow_request()

            latency = time.time() - start

            with self.lock:
                if allowed:
                    self.allowed += 1
                else:
                    self.blocked += 1
                self.latencies.append(latency)

            # traffic shape
            if self.load_profile == "burst":
                # Burst = short sleeps, occasional spikes
                time.sleep(random.uniform(0.0001, 0.005))
            else:
                # Steady = uniform rate
                time.sleep(0.002)

    def run_test(self):
        threads = []

        for _ in range(self.num_threads):
            t = threading.Thread(target=self.request_worker)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        self.print_results()

    def print_results(self):
        print("\n========== Simulation Results ==========")
        print(f"Load Profile: {self.load_profile}")
        print(f"Threads: {self.num_threads}")
        print(f"Duration: {self.duration} seconds")
        print("---------------------------------------")
        print(f"Allowed Requests: {self.allowed}")
        print(f"Blocked Requests: {self.blocked}")
        print(f"Total Requests: {self.allowed + self.blocked}")
        print("---------------------------------------")
        print(f"Average Latency: {sum(self.latencies) / len(self.latencies):.6f} sec")
        print(f"Max Latency: {max(self.latencies):.6f} sec")
        print("========================================\n")


# ===========================
#   RUN PROJECT EXAMPLE
# ===========================

if __name__ == "__main__":
    # Example: 5 tokens max, refill 5 tokens/sec (5 RPS)
    limiter = TokenBucketRateLimiter(
        max_tokens=5,
        refill_rate=5
    )

    print("Running BURST test...\n")
    sim1 = TrafficSimulator(limiter, num_threads=20, duration=4, load_profile="burst")
    sim1.run_test()

    # Re-create limiter for second test
    limiter = TokenBucketRateLimiter(
        max_tokens=5,
        refill_rate=5
    )

    print("Running STEADY test...\n")
    sim2 = TrafficSimulator(limiter, num_threads=20, duration=4, load_profile="steady")
    sim2.run_test()

