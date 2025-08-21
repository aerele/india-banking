from india_banking.install import after_install


def execute():
	# This recreates the India Banking new customization
	# and updates the defaults for the India Banking Settings.
	after_install()
