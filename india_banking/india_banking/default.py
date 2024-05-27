DEFAULT_MODE_OF_TRANSFERS = [
    {
        "mode": "IMPS",
        "minimum_limit": 0,
        "maximum_limit": 200000,
        "start_time": "0:00:00",
        "end_time": "23:59:59",
        "priority": "1"
    },
    {
        "mode": "RTGS",
        "minimum_limit": 200000,
        "maximum_limit": 50000000,
        "start_time": "0:00:00",
        "end_time": "23:59:59",
        "priority": "1"
    },
    {
        "mode": "NEFT",
        "minimum_limit": 0,
        "maximum_limit": 100000000000,
        "start_time": "0:00:00",
        "end_time": "23:59:59",
        "priority": "1"
    },
    {
        "mode": "A2A/FT/Internal",
        "minimum_limit": 0,
        "maximum_limit": 0,
        "start_time": "0:00:00",
        "end_time": "23:59:59",
        "priority": "1"
    }
]

STD_BANK_LIST = [
	{
		'bank_name': 'Yes Bank',
		'swift_number': '',
		'app_name': 'yes_integration_server',
		'is_standard': True
	},
	{
		'bank_name': 'HDFC Bank',
		'swift_number': '',
		'app_name': 'hdfc_integration_server',
		'is_standard': True
	},
	{
		'bank_name': 'ICICI Bank',
		'swift_number': '',
		'app_name': 'icici_integration_server',
		'is_standard': True
	},
	{
		'bank_name': 'Axis Bank',
		'swift_number': '',
		'app_name': 'axis_integration_server',
		'is_standard': True
	}
]
