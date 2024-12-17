DEFAULT_MODE_OF_TRANSFERS = [
	{
		"mode": "IMPS",
		"minimum_limit": 0,
		"maximum_limit": 200000,
		"start_time": "0:00:00",
		"end_time": "23:59:59",
		"disabled": 1,
		"priority": "1",
	},
	{
		"mode": "RTGS",
		"minimum_limit": 200000,
		"maximum_limit": 50000000,
		"start_time": "0:00:00",
		"end_time": "23:59:59",
		"disabled": 1,
		"priority": "1",
	},
	{
		"mode": "NEFT",
		"minimum_limit": 0,
		"maximum_limit": 100000000000,
		"start_time": "0:00:00",
		"end_time": "23:59:59",
		"disabled": 1,
		"priority": "1",
	},
	{
		"mode": "A2A/FT/Internal",
		"minimum_limit": 0,
		"maximum_limit": 0,
		"start_time": "0:00:00",
		"end_time": "23:59:59",
		"disabled": 1,
		"priority": "1",
	},
]

STD_BANK_LIST = [
	"Yes Bank",
	"HDFC Bank",
	"ICICI Bank",
	"Axis Bank",
	"Kotak Mahindra Bank",
]
