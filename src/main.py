#!/usr/bin/python3

import logging.handlers
import sys
import signal
import time
import traceback
import discord_logging
import argparse

log = discord_logging.init_logging(
	backup_count=20
)


