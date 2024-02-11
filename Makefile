# Makefile to copy Solaar udev rules to the appropriate directory

UDEV_RULE_FILE = 42-logitech-unify-permissions.rules
UDEV_RULES_SOURCE := rules.d/$(UDEV_RULE_FILE)
UDEV_RULES_SOURCE_UINPUT := rules.d-uinput/$(UDEV_RULE_FILE)
UDEV_RULES_DEST := /etc/udev/rules.d/

.PHONY: install install_uinput uninstall

install:
	@echo "Copying Solaar udev rules to $(UDEV_RULES_DEST)"
	sudo cp $(UDEV_RULES_SOURCE) $(UDEV_RULES_DEST)
	sudo udevadm control --reload-rules

install_udev_uinput:
	@echo "Copying Solaar udev rules to $(UDEV_RULES_DEST)"
	sudo cp $(UDEV_RULES_SOURCE_UINPUT) $(UDEV_RULES_DEST)
	sudo udevadm control --reload-rules

uninstall:
	@echo "Removing Solaar udev rules from $(UDEV_RULES_DEST)"
	sudo rm -f $(UDEV_RULES_DEST)/$(UDEV_RULE_FILE)
	sudo udevadm control --reload-rules
