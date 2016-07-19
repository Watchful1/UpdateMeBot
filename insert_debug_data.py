import database

database.init()

database.clearSubscriptions()

database.addSubsciption('Watchful12','TestBotSlave1','SubTestBot1')
database.addSubsciption('Watchful12','TestBotSlave2','SubTestBot1')
database.addSubsciption('Watchful12','TestBotSlave3','SubTestBot1')
database.addSubsciption('Watchful12','TestBotSlave4','SubTestBot1')
database.addSubsciption('Watchful12','TestBotSlave1','SubTestBot2')
database.addSubsciption('Watchful12','TestBotSlave2','SubTestBot2')
database.addSubsciption('Watchful12','TestBotSlave5','SubTestBot2')

database.resetAllSubscriptionTimes()
database.close()
