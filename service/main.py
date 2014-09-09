""" This is a service intended to be run periodically as a CRON job.

    It's purpose is to scan Pivotal Tracker and ReviewBoard and append
    a 'reviewed' label to any story that is finished and all its review requests
    have been approved (there must be at least 1 review request for the story in
    order for the service to notice it).

    The service expects a '${HOME}/.workflow.cfg' file with the following
    structure:

    [auth]
    pt_token = <PT_token>
    rb_user = <reviewboard username>
    rb_pwd = <password for the reviewboard user>

    The users (in PT & RB) should have access to all the projects (otherwise the
    service will not be able to update all the stories).
"""

import os
import sys
import rb.extensions
import ConfigParser
import datetime
import random

from slacker import Slacker
from dateutil.relativedelta import relativedelta as delta

CFG_FILE = '%s/.workflow.cfg' % os.environ['HOME']

# How old can the reviews be?
DAYS_DELTA = 5
METAREVIEWER_SLACK_NAME = 'matt'
REVIEW_URL_ROOT = 'https://review.salsitasoft.com/r/'


_slack = None

def notify_user(req):
    try:
        print " >>> sending review id %s" % (req['id'],)
        _slack.chat.post_message(
            '@' + METAREVIEWER_SLACK_NAME,
            "Your lucky metareview URL for today is: %s%s" % 
                (REVIEW_URL_ROOT, req['id']))
    except Exception, e:
        print 'ERROR when notifying user', e


def main():
    global _slack
    # Read the sensitive data from a config file.
    config = ConfigParser.RawConfigParser()
    config.read(CFG_FILE)
    pt_token = config.get('auth', 'pt_token')
    rb_user = config.get('auth', 'rb_user')
    rb_pwd = config.get('auth', 'rb_pwd')
    slack_token = config.get('auth', 'slack_token')

    # HACK: Set the gobal vars.
    _slack = Slacker(slack_token)

    auth = {'username': rb_user, 'password': rb_pwd}
    time_added = datetime.date.today() - delta(days=5)

    # Returns all published unshipped requests.
    reqs = rb.extensions.get_review_requests2(
        {'max-results': 200, 'ship-it': 1, 'last-updated-from': time_added}, auth)

    req = random.choice(reqs)
    notify_user(req)


if __name__ == '__main__':
    main()
