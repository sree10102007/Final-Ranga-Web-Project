import sys
import os

# Add parent directory so goat_farm_app package is importable
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import unittest
import json
from unittest.mock import MagicMock
import goat_farm_app.extensions
import Project_goatfarm

class TestGoatWeights(unittest.TestCase):
    def setUp(self):
        self.app = Project_goatfarm.app
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False

        # Clear the DB connection error flag so before_request guard does not intercept
        self.original_db_error = Project_goatfarm.db_connection_error
        Project_goatfarm.db_connection_error = None

        # Save originals
        self.original_ext_get_db = goat_farm_app.extensions.get_db
        self.original_proj_get_db = Project_goatfarm.get_db

        # Build a shared mock connection
        self.mock_conn = MagicMock()
        self.mock_get_db = MagicMock(return_value=self.mock_conn)

        # Override in both namespaces
        goat_farm_app.extensions.get_db = self.mock_get_db
        Project_goatfarm.get_db = self.mock_get_db

    def tearDown(self):
        Project_goatfarm.db_connection_error = self.original_db_error
        goat_farm_app.extensions.get_db = self.original_ext_get_db
        Project_goatfarm.get_db = self.original_proj_get_db

    # ------------------------------------------------------------------ #
    # POST /goats/<tagNo>/weights - happy path                            #
    # ------------------------------------------------------------------ #
    def test_post_weight_success(self):
        self.mock_conn.execute.return_value.fetchone.side_effect = [
            {'tag_no': 'TEST-GOAT-01'},   # goat exists check
            None,                          # duplicate check returns None (no duplicate on that date)
            {'weight': 18.5}              # latest_entry query returns weight
        ]
        payload = {'weight': 18.5, 'recorded_date': '2026-07-07', 'recorded_by': 'Tester'}
        response = self.client.post(
            '/goats/TEST-GOAT-01/weights',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('added successfully', data['message'])

    # ------------------------------------------------------------------ #
    # POST - reject negative weight                                        #
    # ------------------------------------------------------------------ #
    def test_post_weight_negative(self):
        self.mock_conn.execute.return_value.fetchone.return_value = {'tag_no': 'TEST-GOAT-01'}
        payload = {'weight': -5.0, 'recorded_date': '2026-07-07'}
        response = self.client.post(
            '/goats/TEST-GOAT-01/weights',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('positive number', data['error'].lower())

    # ------------------------------------------------------------------ #
    # POST - reject zero weight                                           #
    # ------------------------------------------------------------------ #
    def test_post_weight_zero(self):
        self.mock_conn.execute.return_value.fetchone.return_value = {'tag_no': 'TEST-GOAT-01'}
        payload = {'weight': 0, 'recorded_date': '2026-07-07'}
        response = self.client.post(
            '/goats/TEST-GOAT-01/weights',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])

    # ------------------------------------------------------------------ #
    # POST - update weight if duplicate date is posted                    #
    # ------------------------------------------------------------------ #
    def test_post_weight_duplicate(self):
        self.mock_conn.execute.return_value.fetchone.side_effect = [
            {'tag_no': 'TEST-GOAT-01'},          # goat exists check
            {'goat_tag_no': 'TEST-GOAT-01'},     # duplicate found -> updates!
            {'weight': 20.0}                     # latest_entry query returns weight
        ]
        payload = {'weight': 20.0, 'recorded_date': '2026-07-07'}
        response = self.client.post(
            '/goats/TEST-GOAT-01/weights',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('updated successfully', data['message'])

    # ------------------------------------------------------------------ #
    # POST - 404 when goat does not exist                                 #
    # ------------------------------------------------------------------ #
    def test_post_weight_goat_not_found(self):
        self.mock_conn.execute.return_value.fetchone.return_value = None
        payload = {'weight': 18.5, 'recorded_date': '2026-07-07'}
        response = self.client.post(
            '/goats/NONEXISTENT/weights',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertFalse(data['success'])

    # ------------------------------------------------------------------ #
    # GET /goats/<tagNo>/weights - returns weight list                    #
    # ------------------------------------------------------------------ #
    def test_get_weights_api(self):
        self.mock_conn.execute.return_value.fetchone.return_value = {'tag_no': 'TEST-GOAT-01'}
        self.mock_conn.execute.return_value.fetchall.return_value = [
            {
                'id': 1,
                'weight': 22.0,
                'unit': 'kg',
                'recorded_date': '2026-07-06',
                'recorded_by': 'Tester',
                'created_at': '2026-07-06T12:00:00',
            }
        ]
        response = self.client.get('/goats/TEST-GOAT-01/weights')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['records']), 1)
        self.assertEqual(data['records'][0]['weight'], 22.0)

    # ------------------------------------------------------------------ #
    # GET - 404 when goat does not exist                                  #
    # ------------------------------------------------------------------ #
    def test_get_weights_goat_not_found(self):
        self.mock_conn.execute.return_value.fetchone.return_value = None
        response = self.client.get('/goats/GHOST-TAG/weights')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertFalse(data['success'])

    # ------------------------------------------------------------------ #
    # GET /goats/weights/summary - returns weight summaries               #
    # ------------------------------------------------------------------ #
    def test_get_weights_summary(self):
        self.mock_conn.execute.return_value.fetchall.return_value = [
            {'tag_no': 'TEST-GOAT-01', 'status': 'Active', 'weight_kg': 15.0}
        ]
        self.mock_conn.execute.return_value.fetchone.side_effect = [
            [1], # count query returns 1
            {'weight': 15.0, 'unit': 'kg', 'recorded_date': '2026-07-06'} # latest_row query
        ]
        response = self.client.get('/goats/weights/summary')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['summary']), 1)
        self.assertEqual(data['summary'][0]['tag_no'], 'TEST-GOAT-01')
        self.assertEqual(data['summary'][0]['weight_records_count'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
