import json
import unittest

from core.operations_parser import OperationParseError, parse_operations


class OperationsParserTests(unittest.TestCase):
    def test_parse_valid_operations(self) -> None:
        payload = {
            "operations": [
                {"type": "read", "path": "docs/readme.txt"},
                {"type": "write", "path": "docs/out.txt", "mode": "overwrite", "content": "hello"},
                {"type": "move", "src": "a.txt", "dst": "b.txt"},
                {"type": "mkdir", "path": "dir"},
            ]
        }
        ops = parse_operations(json.dumps(payload))
        self.assertEqual(len(ops), 4)
        self.assertEqual(ops[1].type, "write")
        self.assertEqual(ops[1].mode, "overwrite")

    def test_reject_invalid_json(self) -> None:
        with self.assertRaises(OperationParseError):
            parse_operations("not-json")

    def test_reject_missing_operations(self) -> None:
        with self.assertRaises(OperationParseError):
            parse_operations(json.dumps({"foo": []}))

    def test_reject_invalid_type(self) -> None:
        payload = {"operations": [{"type": "rm", "path": "x"}]}
        with self.assertRaises(OperationParseError):
            parse_operations(json.dumps(payload))

    def test_reject_missing_path(self) -> None:
        payload = {"operations": [{"type": "read"}]}
        with self.assertRaises(OperationParseError):
            parse_operations(json.dumps(payload))

    def test_reject_write_without_mode(self) -> None:
        payload = {"operations": [{"type": "write", "path": "x", "content": "y"}]}
        with self.assertRaises(OperationParseError):
            parse_operations(json.dumps(payload))

    def test_reject_unknown_fields(self) -> None:
        payload = {"operations": [{"type": "read", "path": "x", "foo": "bar"}]}
        with self.assertRaises(OperationParseError):
            parse_operations(json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
