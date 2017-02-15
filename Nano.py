import discord
import json
import asyncio
import random
import os
import sys
import datetime
from models import *

f = open('config','r')
config = json.load(f)

print(config)
image_directory =  config['image_directory']
owner_id = discord.User(id=config['owner_id'])
rand_cd = config['rand_cd']
daily_rand_allowance = config['daily_rand_allowance']

client = discord.Client()
battles_ongoing = {}
rand_user_cd_list = {}
qtb_roles = {}

class qt_battle():
    def __init__(self):
        self.girls = [QtAnimeGirl(), QtAnimeGirl()]
        self.caller = discord.User()
        self.vote = discord.Message()
        # TODO: These should REALLY be attributes of a QtAnimeGirl
        self.vote_A = 0
        self.vote_B = 0
        self.voters = {}
        self.is_ongoing = True
        self.time_start = datetime.datetime.now()
    def name(self, girl, new_name):
        # 'girl' should be either 1 or 2.
        # I've done some ripping here so it might be buggy, beware.
        self.girls[girl - 1].name = new_name
        session.commit()
    def vote_girl(self, girl, author):
        letter = 'A' if girl == 1 else 'B'
        if author in self.voters:
            # I don't know why we're using 'is' here instead of '=='.
            # I'm leaving it like this, because else it might break.
            if self.voters[author] is 2:
                self.vote_B -= 1
            else:
                self.vote_A -= 1
        setattr(self, "vote_{0}".format(letter), getattr(self, "vote_{0}".format(letter)) + 1)
        self.voters[author] = girl
    def tag(self, girl, message):
        # TODO: Comment this hideous regex.
        # Probably rewrite it too.

        split_content = message.split(' ')
        tags = split_content[2].split(',')

        for tag in tags:
            self.girls[girl-1].addTag(tag)

        return ', '.join(tags)
    def tags(self, girl):
        tags = []
        for x in self.girls[girl-1].tags:
            tags.append(x.tag)
        return ', '.join(tags)
    def end(self):
        draw = (self.vote_A == self.vote_B)
        if not draw:
            winner = 1 if max(self.vote_A, self.vote_B) == self.vote_A else 2
            # Relies on the fact that 3 - 2 = 1 and 3 - 1 = 2.
            loser = 3 - winner
            oldELO = self.girls[winner - 1].elo
            self.girls[winner - 1].updateELO(self.girls[loser - 1].elo, 1)
            self.girls[loser - 1].updateELO(self.girls[winner - 1].elo, 0)
            return '{0} Wins! Her rating is now {1}(+{2})'.format(self.girls[winner - 1],
                                                                  self.girls[winner - 1].elo,
                                                                  self.girls[winner - 1].elo - oldELO)
        else:
            old_ELO_A = self.girls[0].elo
            old_ELO_B = self.girls[1].elo
            self.girls[0].updateELO(self.girls[1].elo, 0.5)
            self.girls[1].updateELO(self.girls[0].elo, 0.5)
            return "It's a tie! QTR change: {} ({})  {} ({})".format(self.girls[0],
                                                                     self.girls[0].elo - old_ELO_A,
                                                                     self.girls[1],
                                                                     self.girls[1].elo - old_ELO_B)

@client.event
async def on_ready():
    print('''Logged in as\n{0}\n{1}\n------
        '''.format(client.user.name, client.user.id))
    for server in client.servers:
        qtb_roles[server] = discord.utils.get(server.roles, name='qtb')

@client.event
async def on_message(message):
    if(message.content.startswith('>qtbattle')
       or message.content.startswith('>qtb')
       and not message.channel in battles_ongoing):
        all_girls = []
        battle = qt_battle()
        battles_ongoing[message.channel] = battle
        print('Starting QT battle')

        battle.caller = message.author



        if message.content == ('>qtb') or message.content == ('>qtbattle'):
            all_girls = session.query(QtAnimeGirl).all()
        else:
            tags = message.content.split(' ')[1].split(',')
            for tag in tags:
                try:
                    tag_object = session.query(Tag).filter(Tag.tag == tag).one()
                    girls_with_tag = tag_object.qtanimegirls
                    for x in girls_with_tag:
                        if x.id not in all_girls:
                            all_girls.append(x.id)
                except NoResultFound:
                    pass
            if len(all_girls) >= 2:
                all_girls = session.query(QtAnimeGirl).filter(QtAnimeGirl.id.in_(all_girls)).all()
            else:
                tmp = await client.send_message(message.channel,
                                                "Couldn't find enough girls with provided tags, using random girls")
                all_girls = session.query(QtAnimeGirl).all()

        battle.girls = random.sample(list(all_girls), 2)

        print('Girl 1 = {}({})'.format(battle.girls[0].id, battle.girls[0].elo))
        print('Girl 2 = {}({})'.format(battle.girls[1].id, battle.girls[1].elo))
        print('--------------')

        starting_msg = await client.send_message(message.channel,'Starting {}!'.format(qtb_roles[message.server].mention))
        await client.send_typing(message.channel)
        await client.send_file(message.channel,
                               open(os.path.join(image_directory, battle.girls[0].image), 'rb'),
                               filename=battle.girls[0].image,
                               content='{0} with a {1} ranking'.format(battle.girls[0], battle.girls[0].elo))
        await client.send_typing(message.channel)
        await client.send_file(message.channel,
                               open(os.path.join(image_directory, battle.girls[1].image), 'rb'),
                               filename=battle.girls[1].image,
                               content='{0} with a {1} ranking'.format(battle.girls[1], battle.girls[1].elo))
        try:
            await client.delete_message(starting_msg)
            await client.delete_message(tmp)
        # FIXME: Bare exception - what exception does this throw?
        except:
            pass

        battle.vote = await client.send_message(message.channel,
                                                '%s vs %s - 0 - 0' % (battle.girls[0], battle.girls[1]))
        battle.time_start = datetime.datetime.now()
        battles_ongoing[message.channel] = battle

    elif (message.content.startswith('>qtbattle')
          or message.content.startswith('>qtb')
          and message.channel in battles_ongoing):
        await client.send_message(message.channel, 'Only 1 ongoing battle per channel!')

    if message.channel in battles_ongoing:
        battle = battles_ongoing[message.channel]

        if message.content.startswith('>name'):

            split_content = message.content.split(' ')
            girl = int(split_content[1])
            battle.name(girl, split_content[2])
            await client.send_message(message.channel,
                                      'Girl {0} now known as {1}!'.format(battle.girls[girl - 1].id,
                                                                          battle.girls[girl - 1]))
        message.content = message.content.lower()
        if message.content.startswith('>vote'):
            if message.content[6] == '1' or message.content[6] == '2':
                girl = int(message.content[6])
                battle.vote_girl(girl, message.author)
                # TODO: This is ugly. Maybe votes should be a property of QtAnimeGirl objects?
                await client.edit_message(battle.vote, '%s vs %s - %s - %s' % (battle.girls[0],
                                                                               battle.girls[1],
                                                                               battle.vote_A,
                                                                               battle.vote_B))
        elif message.content.startswith('>tag '):
            # Space after '>tag' otherwise '>tags' would also pass
            girl = int(message.content[5])
            await client.delete_message(message)
            s = battle.tag(girl, message.content)
            await client.send_message(message.channel, 'Tags {} added to {}'.format(s, battle.girls[girl - 1]))
        elif message.content.startswith('>tags'):
            girl = int(message.content[6])
            await client.delete_message(message)
            tags = battle.tags(girl)
            await client.send_message(message.channel, "{}'s tags: {}".format(battle.girls[girl - 1], tags))
        elif (message.content.startswith('>end')
              and ((message.author == battle.caller) or (message.author == owner_id))):
            battle.is_ongoing = False

        timedelta = datetime.datetime.now() - battle.time_start
        if timedelta.seconds > 180 or not battle.is_ongoing:
            del battles_ongoing[message.channel]
            end_message = battle.end()
            await client.send_message(message.channel, end_message)

    if message.content.startswith('>tagid'):
        split_content = message.content.split(' ')
        girl_id = int(split_content[1])
        tags = split_content[2].split(',')

        girl = session.query(QtAnimeGirl).filter(QtAnimeGirl.id == girl_id).one()

        for tag in tags:
            girl.addTag(tag)

        if len(tags) == 1:
            info = await client.send_message(message.channel,'Tag {} added to {}!'.format(tags[0],girl.id))
        else:
            info = await client.send_message(message.channel,'Tags {} added to {}!'.format((', '.join(tags)),girl.id))

        await client.delete_message(message)
        await asyncio.sleep(30)
        await client.delete_message(info)

    # This part is unbelievably bad, but I don't see an easy fix right now.
    # TODO: Rewrite all of this.
    elif message.content.startswith('>bestgirl'):
        all_girls = session.query(QtAnimeGirl).order_by(QtAnimeGirl.elo).all()
        first = all_girls[len(all_girls)-1]
        best_girls = []
        x = 1
        while first.elo == all_girls[len(all_girls)-x].elo:
            best_girls.append(all_girls[len(all_girls)-x])
            x += 1

        if len(best_girls) > 1:
            await client.send_message(message.channel, "It's a tie between {} girls!".format(len(best_girls)))
            for x in best_girls:
                await client.send_typing(message.channel)
                await client.send_file(
                    message.channel,
                    open(os.path.join(image_directory, x.image), 'rb'),
                    filename=x.image,
                    content='{0} with a {1} ranking'.format(x, x.elo))
        else:
            await client.send_message(message.channel, "Best girl!")
            await client.send_file(
                message.channel,
                open(os.path.join(image_directory, best_girls[0].image), 'rb'),
                filename=best_girls[0].image,
                content='{0} with a {1} ranking'.format(best_girls[0], best_girls[0].elo))

    elif message.content.startswith('>worstgirl'):
        all_girls = session.query(QtAnimeGirl).order_by(QtAnimeGirl.elo).all()
        first = all_girls[0]
        worstgirl = []
        x = 0
        while first.elo == all_girls[x].elo:
            worstgirl.append(all_girls[x])
            x += 1

        if len(worstgirl) > 1:
            await client.send_message(message.channel, "It's a tie between {} girls!".format(len(worstgirl)))
            for x in worstgirl:
                await client.send_typing(message.channel)
                await client.send_file(
                    message.channel,
                    open(os.path.join(image_directory, x.image), 'rb'),
                    filename=x.image,
                    content='{0} with a {1} ranking'.format(x, x.elo))
        else:
            await client.send_message(message.channel, "Worst girl!")
            await client.send_file(
                message.channel,
                open(os.path.join(image_directory, worstgirl[0].image), 'rb'),
                filename=worstgirl[0].image,
                content='{0} with a {1} ranking'.format(worstgirl[0], worstgirl[0].elo))

    elif (message.content.startswith('>averagegirl') or message.content.startswith('>avggirl')):
        elo = session.query(func.avg(QtAnimeGirl.elo)).all()
        averagegirl = random.choice(session.query(QtAnimeGirl).filter(QtAnimeGirl.elo == int(elo[0][0])).all())

        await client.send_message(message.channel, "Most average girl!")
        await client.send_file(
            message.channel,
            open(os.path.join(image_directory, averagegirl.image), 'rb'),
            filename=averagegirl.image,
            content='{0} with a {1} ranking'.format(averagegirl, averagegirl.elo))

    elif message.content.startswith('>updategirls') and message.author == owner_id:
        anime_girl = QtAnimeGirl()
        new_girls = anime_girl.get_new_girls(image_directory)
        await client.send_message(message.channel, "{} new girls added!".format(new_girls))

    elif message.content.startswith('>addme'):
        await client.add_roles(message.author,qtb_roles[message.server])
        info_msg =  await client.send_message(message.channel,'Added {} to {}'.format(message.author.mention,qtb_roles[message.server].mention))
        await asyncio.sleep(30)
        await client.delete_message(info_msg)

    elif message.content.startswith('-randqt'):

        # FIXME: Redefinition from str to list.
        all_girls = []
        info = ''
        if message.content == ('-randqt'):
            all_girls = session.query(QtAnimeGirl).all()
        else:
            #remove whitespace and split into tags
            tags = message.content.replace('-randqt','').replace(' ','').split(',')
            query = session.query(QtAnimeGirl)
            #Establish a fallback query
            working_query = session.query(QtAnimeGirl)
            for tag in tags:
                query = query.filter(QtAnimeGirl.tags.any(tag = tag))
                #Check if query is valid
                all_girls = query.all()
                if all_girls > []:
                    #If it is
                    #add the same query to the fallback query
                    working_query = working_query.filter(QtAnimeGirl.tags.any(tag = tag))
                else:
                    #If it isn't revert
                    query = working_query

            all_girls = query.all()
            #This is a dirty fucking hack, but I'm not sure how else to do this
            if query.all() == session.query(QtAnimeGirl).all():
                info = 'No girls found with provided tags'

        girl = random.choice(all_girls)
        #If girl found with provided tags list them
        if not info:
            tag_objects = girl.tags
            tags = []
            for x in tag_objects:
                tags.append(x.tag)
            info = ', '.join(tags)

        await client.send_typing(message.channel)
        qt = await client.send_file(
            message.channel,
            open(os.path.join(image_directory, girl.image), 'rb'),
            filename=girl.image,
            content='Random QT! {} id{} [{}]'.format(girl.name, girl.id, info))
        await asyncio.sleep(60)
        await client.delete_message(message)
        await client.delete_message(qt)

    elif message.content.startswith('-rand'):

        param = int(message.content.split(' ')[1])
        mention = message.author.mention

        try:
            #check if rand_allowence_left needs to  be reset
            if message.author not in rand_user_cd_list or rand_user_cd_list[message.author]['date'].date() < datetime.datetime.now().date():
                rand_user_cd_list[message.author]={'rand_allowance_left' : daily_rand_allowance, 'date' : datetime.datetime.now(), 'last_rand' : datetime.datetime.now()}
            if ((rand_user_cd_list[message.author]['rand_allowance_left'] <= 0)
            and (datetime.datetime.now() - rand_user_cd_list[message.author]['last_rand']).seconds > rand_cd):
                await client.send_message(message.channel,
                                          '{} rolled **{}**'.format(mention, random.randint(0, param)))
                rand_user_cd_list[message.author]['last_rand']=datetime.datetime.now()

            elif message.author in rand_user_cd_list and rand_user_cd_list[message.author]['rand_allowance_left'] > 0:
                await client.send_message(message.channel,
                                          '{} rolled **{}**'.format(mention, random.randint(0, param)))
                rand_user_cd_list[message.author]['last_rand']=datetime.datetime.now()
                rand_user_cd_list[message.author]['rand_allowance_left'] -= 1

            else:
                await client.send_message(message.channel,'**Rand** is still on cooldown')
        # FIXME: Bare except
        except ValueError:
            pass

    elif message.content.startswith('>setgame') and (message.author == owner_id):
        game = discord.Game(name=message.content.split(' ')[1])
        await client.change_status(game)

    elif message.content.startswith('>help'):
        await client.send_message(
            message.channel,
            '''
           ```Hakase commands:
           ---------
           >qtbattle tags*------Start qt battle (*optional, seperated by commas)
           -rand argument ------Random number
           -randqt tags* -------Random qt (*optional, seperated by commas)
           >bestgirl -----------Shows girl or girls with the highest rating
           >worstgirl ----------Shows girl or girls with the lowest rating

           While in QTBattle:
           ---------
           >vote 1/2 -----------Vote for girl
           >tag 1/2 tag1,tag2 --Tag girl
           >tags 1/2 -----------See girls tags
           >name 1/2 name ------Gives girl a name
           >end ----------------Ends QTBattle(user who started it only)
           ```
           ''')

    elif message.content.startswith('-denko'):
        await client.delete_message(message)
        await client.send_message(message.channel, '(´・ω・`)')

    if 'turtle' in message.content or '🐢' in message.content:
        await client.send_message(message.channel, '''```
  _
 (*\.-.
  \/___\_
   U   U
        ```''')
        
if __name__ == "__main__":
    client.run(config['client_key'])
