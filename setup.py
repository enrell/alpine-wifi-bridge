#!/usr/bin/env python3
import sys
import click
from pybridge.utils import ensure_root, log
from pybridge.config import load_config, save_runtime_config
from pybridge.backup import backup_network_config, restore_settings
from pybridge.network import install_packages, detect_interfaces, setup_wifi, detect_gateway_ip, setup_ethernet, setup_routing
from pybridge.firewall import setup_firewall, save_firewall_rules
from pybridge.portforward import setup_port_forwarding, remove_port_forwarding

CONFIG_PATH = 'config/settings.conf'
RUNTIME_CONFIG = '/etc/alpine-wifi-bridge/config'

@click.group()
@click.pass_context
def cli(ctx):
    "Main entry point for Alpine Wi-Fi Bridge setup"
    ensure_root()
    ctx.obj = {}

@cli.command()
@click.option('--config', default=CONFIG_PATH, help='Path to configuration file')
def setup(config):
    "Perform full setup of Wi-Fi bridge"
    log('Starting setup...')
    cfg = load_config(config)
    backup_network_config(cfg)
    install_packages()
    detect_interfaces(cfg)
    setup_wifi(cfg)
    detect_gateway_ip(cfg)
    setup_ethernet(cfg)
    setup_routing(cfg)
    setup_firewall(cfg)
    setup_port_forwarding(cfg)
    save_firewall_rules(cfg)
    save_runtime_config(cfg, RUNTIME_CONFIG)
    log('Setup complete.')

@cli.command()
@click.option('--config', default=CONFIG_PATH, help='Path to configuration file')
def restore(config):
    "Restore original network settings"
    log('Starting restore...')
    cfg = load_config(RUNTIME_CONFIG if sys.argv[1] == '--restore' else config)
    remove_port_forwarding(cfg)
    restore_settings(cfg)
    log('Restore complete.')

if __name__ == '__main__':
    cli()