###
# Copyright (c) 2013, MrLoom
# All rights reserved.
#
#
###

import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('RfK', True)


RfK = conf.registerPlugin('RfK')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(RfK, 'someConfigVariableName',
#     registry.Boolean(False, """Help for someConfigVariableName."""))
conf.registerGlobalValue(RfK, 'queryURL',
    registry.String('', """Radio server query URL"""))
conf.registerGlobalValue(RfK, 'queryPass',
    registry.String('', """Radio server query pass""", private=True))
conf.registerGlobalValue(RfK, 'httpProxy',
    registry.String('', """HTTP proxy to use for radio queries""", private=True))
conf.registerGlobalValue(RfK, 'enablePolling',
    registry.Boolean(False, """Enable polling of radio server"""))
conf.registerGlobalValue(RfK, 'pollingInterval',
    registry.PositiveInteger(15, """Interval at which to poll the radio server"""))
conf.registerChannelValue(RfK, 'announce',
    registry.Boolean(False, """Announce radio status on this channel"""))
conf.registerChannelValue(RfK, 'announcePrefix',
    registry.String('[RfK]', """Prefix for every announment made"""))
conf.registerGlobalValue(RfK, 'maxStringLength',
    registry.PositiveInteger(140, """Allowed string length before shortener kicks in"""))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
