import unittest
import json
from vacuula_server.state import PendingRequest, pending_requests, abort_pending_requests
from vacuula_server.conn import RobotConn, Gen2Gen3Conn
from vacuula_server.generation import Generation

class TestPendingRequests(unittest.TestCase):
    def setUp(self):
        pending_requests.clear()

    def tearDown(self):
        pending_requests.clear()

    def test_abort_only_matching_connection(self):
        # Create two distinct connections for the same serial (reconnect scenario)
        conn_old = RobotConn("SERIAL-1", Generation.GEN3, Gen2Gen3Conn("pass", None))
        conn_new = RobotConn("SERIAL-1", Generation.GEN3, Gen2Gen3Conn("pass", None))

        slot_old = PendingRequest()
        slot_old.conn = conn_old
        pending_requests["101"] = slot_old

        slot_new = PendingRequest()
        slot_new.conn = conn_new
        pending_requests["102"] = slot_new

        # Abort the old connection
        aborted = abort_pending_requests(conn_old, status=503, message="Robot disconnected")
        self.assertEqual(aborted, 1)

        # slot_old must be fulfilled and aborted
        self.assertTrue(slot_old.event.is_set())
        self.assertEqual(slot_old.status, 503)
        data = json.loads(slot_old.content.decode("utf-8"))
        self.assertEqual(data.get("error"), "Robot disconnected")

        # slot_new must NOT be touched or fulfilled
        self.assertFalse(slot_new.event.is_set())
        self.assertIsNone(slot_new.status)
        self.assertIsNone(slot_new.content)

    def test_abort_multiple_slots_on_same_connection(self):
        conn = RobotConn("SERIAL-2", Generation.GEN3, Gen2Gen3Conn("pass", None))

        s1 = PendingRequest()
        s1.conn = conn
        pending_requests["201"] = s1

        s2 = PendingRequest()
        s2.conn = conn
        pending_requests["202"] = s2

        aborted = abort_pending_requests(conn, status=503)
        self.assertEqual(aborted, 2)
        self.assertTrue(s1.event.is_set())
        self.assertTrue(s2.event.is_set())

    def test_already_fulfilled_slot_not_reaborted(self):
        conn = RobotConn("SERIAL-3", Generation.GEN3, Gen2Gen3Conn("pass", None))
        s = PendingRequest()
        s.conn = conn
        s.fulfill(b'{"result": "ok"}', 200)
        pending_requests["301"] = s

        aborted = abort_pending_requests(conn, status=503)
        self.assertEqual(aborted, 0)
        self.assertEqual(s.status, 200)

if __name__ == "__main__":
    unittest.main()
