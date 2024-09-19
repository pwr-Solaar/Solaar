UDEV_RULE_FILE = 42-logitech-unify-permissions.rules
UDEV_RULES_SOURCE := rules.d/$(UDEV_RULE_FILE)
UDEV_RULES_SOURCE_UINPUT := rules.d-uinput/$(UDEV_RULE_FILE)
UDEV_RULES_DEST := /etc/udev/rules.d/

PIP_ARGS ?= .

.PHONY: install_ubuntu install_macos
.PHONY: install_apt install_brew install_pip
.PHONY: install_udev install_udev_uinput reload_udev uninstall_udev
.PHONY: format lint test

install_ubuntu: install_apt install_udev_uinput install_pip

install_macos: install_brew install_pip

install_apt:
	@echo "Installing Solaar dependencies via apt"
	sudo apt update
	sudo apt install libdbus-1-dev libglib2.0-dev libgtk-3-dev libgirepository1.0-dev

install_dnf:
	@echo "Installing Solaar dependencies via dn"
	sudo dnf install gtk3 python3-gobject python3-dbus python3-pyudev python3-psutil python3-xlib python3-yaml

install_brew:
	@echo "Installing Solaar dependencies via brew"
	brew update
	brew install hidapi gtk+3 pygobject3 gobject-introspection

install_pip:
	@echo "Installing Solaar via pip"
	python -m pip install --upgrade pip
	pip install $(PIP_ARGS)

install_pipx:
	@echo "Installing Solaar via pipx"
	pipx install --system-site-packages $(PIP_ARGS)

install_udev:
	@echo "Copying Solaar udev rule to $(UDEV_RULES_DEST)"
	sudo cp $(UDEV_RULES_SOURCE) $(UDEV_RULES_DEST)
	make reload_udev

install_udev_uinput:
	@echo "Copying Solaar udev rule (uinput) to $(UDEV_RULES_DEST)"
	sudo cp $(UDEV_RULES_SOURCE_UINPUT) $(UDEV_RULES_DEST)
	make reload_udev

reload_udev:
	@echo "Reloading udev rules"
	sudo udevadm control --reload-rules

uninstall_udev:
	@echo "Removing Solaar udev rules from $(UDEV_RULES_DEST)"
	sudo rm -f $(UDEV_RULES_DEST)/$(UDEV_RULE_FILE)
	make reload_udev

format:
	@echo "Formatting Solaar code"
	ruff format .

lint:
	@echo "Linting Solaar code"
	ruff check . --fix

test:
	@echo "Running Solaar tests"
	pytest --cov --cov-report=xml
