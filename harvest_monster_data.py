from bs4 import BeautifulSoup
from functools import reduce
import json
import re
import requests
import time
import traceback

PSB_CONSTANT = 'bludgeoning, piercing, and slashing'
PSB_CONSTANT_ALTER = 'bludgeoning, piercing and slashing'  # specially made for the tarrasque


# Currently takes session as a parameter... this should be a managed object which internally maintains a session
def parse_monster_from_aidedd_link(session, url):
    monster_data = {}

    monster_raw_html = session.get(url).text
    monster_html = BeautifulSoup(monster_raw_html, 'html.parser')
    # 'bloc' is specific to aidedd.org
    stat_block = monster_html.find_all('div', class_='bloc')[0]

    monster_data['name'] = stat_block.h1.get_text()

    # Parse out the size, family, and alignment... because they're all on the same line?
    type_text = stat_block.find_all('div', class_='type')[0].get_text()
    type_text_regex = '([A-z]+) ([A-z ()]+), ([A-z \-]+)'
    type_text_params = re.search(type_text_regex, type_text)
    if type_text_params != None:
        monster_data['size'] = type_text_params.group(1).lower()
        monster_data['family'] = type_text_params.group(2)
        # TODO: support genus in family (e.g humanoid (aarakocra))
        monster_data['alignment'] = type_text_params.group(3).lower()
    else:
        raise Exception('Unexpected Type format!')

    monster_attributes = {}
    block = stat_block.find_all('div', class_='red')[0]
    attribute_regex = '<strong>(.+?)<\/strong>(.+?)(?=<|\n)'
    attributes = re.findall(attribute_regex, str(block))
    for attribute in attributes:
        key = attribute[0].lower().replace(' ', '_')
        value = attribute[1].replace('<br/>', '').replace('<b>', '').replace('<i>', '').lower().strip()

        if key in ('saving_throws', 'skills'):
            pairs = [pair.strip().split(' ') for pair in value.split(',')]
            monster_entries = {}
            for pair in pairs:
                monster_entries[pair[0]] = int(pair[1])
            monster_data[key] = monster_entries
        elif key in ['armor_class', 'hit_points']:
            monster_data[key] = int(value.split(' ')[0])
        elif key in ['challenge']:
            cr_text = value.split(' ')[0]
            if '/' in cr_text:
                fraction_parts = cr_text.split('/')
                monster_data[key] = float(fraction_parts[0]) / float(fraction_parts[1])
            else:
                monster_data[key] = float(cr_text)
        elif key in ['damage_immunities', 'damage_resistances', 'damage_vulnerabilities']:
            # The problem is the delimiter changes for PSB type resistances.
            # e.g: "fire, poison; bludgeoning, piercing and slashing from nonmagical attacks"
            # We need to filter out the PSB types, then process everything normally
            value = value.replace(PSB_CONSTANT_ALTER, PSB_CONSTANT)
            psb_types = list(filter(lambda type: PSB_CONSTANT in type,
                                    value.split(';')))
            non_psb_types = reduce(lambda agg, add: agg + "," + add,
                                   filter(lambda type: PSB_CONSTANT not in type,
                                          value.split(';')), '')
            monster_data[key] = list(filter(None,
                                            [type.strip() for type in non_psb_types.split(',')] + [type.strip() for type
                                                                                                   in psb_types]))
        elif key in ['condition_immunities', 'languages', 'senses']:
            monster_data[key] = [thing.strip() for thing in value.split(',')]
        elif key == 'speed':
            speeds = []
            for speed in value.split(','):
                components = speed.strip().split(' ')

                # Check if the speed type is implicit (and therefore walking) by testing the first component
                # e.g ['40', 'ft.'] implies walking because the first value is 40 and therefore an int
                is_walking_speed_type = True
                try:
                    int(components[0])
                except:
                    is_walking_speed_type = False
                if is_walking_speed_type:
                    speeds.append({'type': 'walk',
                                   'speed': int(components[0]),
                                   'note': ' '.join(components[2:])})
                else:
                    # TODO: Consider not writing 'note' when it's just going to be blank... below and above this line
                    speeds.append({'type': components[0],
                                   'speed': int(components[1]),
                                   'note': ' '.join(components[3:])})
            monster_data['movement_options'] = speeds
        elif key in ['cha', 'con', 'dex', 'int', 'str', 'wis']:
            monster_attributes[key] = int(value.split(' ')[0])
        else:
            monster_data[key] = value
    monster_data['attributes'] = monster_attributes

    # Collect monster features
    # This code sucks, but it's also crazy parsing code and doesn't need to be perfect.
    # Phase 1: Monster features in p tags
    # Phase 1 ends when there is a div with class 'rub' and with the text ACTIONS
    # Phase 2: Monster actions
    # TODO: What about reactions? Legendary actions?
    phase = 1
    monster_features = {}
    monster_actions = {}
    for feature_html in stat_block.find('div', class_='sansSerif').find_all(['p', 'div'], recursive=False):
        # We always ignore divs, but some of them indicate the p blocks have changed from features to actions
        if feature_html.name == 'div':
            if 'class' in feature_html.attrs and 'rub' in feature_html.attrs['class']:
                phase = 2
            continue
        elif feature_html.name == 'p':
            if phase == 1:
                # This doesn't seem to handle features like the efreeti's innate spellcasting
                monster_features[feature_html.contents[0].text] = {
                    'description': ''.join(
                        map(lambda x: x.text if getattr(x, "text", None) else x, feature_html.contents[1:]))[2:]}
            elif phase == 2:
                complex_attack_regex = '''([A-z]+). ([A-z]+) Weapon Attack: ([+\-0-9]+) to hit, reach ([0-9]+) ft., ([A-z ]+). Hit: ([0-9]+) \(([ d+\-0-9]+)\) ([A-z ]+) damage plus ([0-9]+) \(([ d+\-0-9]+)\) ([A-z ]+) damage([\(\)\.,' 0-9A-z ]+)'''
                complex_attack_attributes = re.search(complex_attack_regex, feature_html.text)
                if complex_attack_attributes:
                    attack = {'type': 'attack'}
                    attack['name'] = complex_attack_attributes.group(1)
                    attack['attack_type'] = complex_attack_attributes.group(2).lower()
                    attack['to_hit'] = int(complex_attack_attributes.group(3))
                    attack['reach'] = int(complex_attack_attributes.group(4))
                    attack['target'] = complex_attack_attributes.group(5)
                    attack['expected_damage'] = int(complex_attack_attributes.group(6))
                    attack['damage_string'] = complex_attack_attributes.group(7)
                    attack['damage_type'] = complex_attack_attributes.group(8)
                    attack['secondary_expected_damage'] = int(complex_attack_attributes.group(9))
                    attack['secondary_damage_string'] = complex_attack_attributes.group(10)
                    attack['secondary_damage_type'] = complex_attack_attributes.group(11)
                    attack['additional'] = complex_attack_attributes.group(12)[2:]
                    monster_actions[attack['name'].lower()] = attack
                else:
                    attack_regex = '''([A-z]+). ([A-z]+) Weapon Attack: ([+\-0-9]+) to hit, reach ([0-9]+) ft., ([A-z ]+). Hit: ([0-9]+) \(([ d+\-0-9]+)\) ([A-z ]+) damage([\(\)\.,' 0-9A-z ]+)'''
                    attack_attributes = re.search(attack_regex, feature_html.text)
                    # TODO: support limited use actions (e.g Enlarge (one per short or long rest))
                    # TODO: attack type can also be 'Melee or Ranged Weapon Attack' but we only expect one word right now...
                    if attack_attributes:
                        attack = {'type': 'attack'}
                        attack['name'] = attack_attributes.group(1)
                        attack['attack_type'] = attack_attributes.group(2).lower()
                        attack['to_hit'] = int(attack_attributes.group(3))
                        attack['reach'] = int(attack_attributes.group(4))
                        attack['target'] = attack_attributes.group(5)
                        attack['expected_damage'] = int(attack_attributes.group(6))
                        attack['damage_string'] = attack_attributes.group(7)
                        attack['damage_type'] = attack_attributes.group(8)
                        attack['additional'] = attack_attributes.group(9)[2:]
                        monster_actions[attack['name'].lower()] = attack

                # Parse multi-attacks... there's three, no four, formats I've seen so far
                # TODO: Abstract these into functions to avoid namespace pollution
                simple_multi_attack_regex = '''Multiattack. The [A-z ]+ makes ([A-z]+) ([A-z]+) attacks.'''
                simple_multi_attack_attributes = re.search(simple_multi_attack_regex, feature_html.text)
                if simple_multi_attack_attributes:
                    multi_attack = {'type': 'multi_attack', 'attacks': []}
                    multi_attack['attacks'].append({
                        'quantity': number_string_to_number(simple_multi_attack_attributes.group(1)),
                        'attack': simple_multi_attack_attributes.group(2)})
                    monster_actions['multi_attack'] = multi_attack
                complex_multi_attack_regex = '''Multiattack. The [A-z ]+ makes [A-z]+ attacks: ([A-z]+) with its ([A-z]+) and ([A-z]+) with its ([A-z]+)'''
                complex_multi_attack_attributes = re.search(complex_multi_attack_regex, feature_html.text)
                if complex_multi_attack_attributes:
                    multi_attack = {'type': 'multi_attack', 'attacks': []}
                    multi_attack['attacks'].append({
                        'quantity': number_string_to_number(complex_multi_attack_attributes.group(1)),
                        'attack': complex_multi_attack_attributes.group(2)})
                    multi_attack['attacks'].append({
                        'quantity': number_string_to_number(complex_multi_attack_attributes.group(3)),
                        'attack': complex_multi_attack_attributes.group(4)})
                    monster_actions['multi_attack'] = multi_attack
                really_complex_multi_attack_regex = '''Multiattack. The [A-z ]+ can use its ([A-z ]+). It then makes [A-z]+ attacks: ([A-z]+) with its ([A-z]+) and ([A-z]+) with its ([A-z]+)'''
                really_complex_multi_attack_attributes = re.search(really_complex_multi_attack_regex, feature_html.text)
                if really_complex_multi_attack_attributes:
                    multi_attack = {'type': 'multi_attack', 'attacks': []}
                    multi_attack['attacks'].append({
                        'quantity': 1,
                        'optional': True,
                        'attack': really_complex_multi_attack_attributes.group(1)})
                    multi_attack['attacks'].append({
                        'quantity': number_string_to_number(really_complex_multi_attack_attributes.group(2)),
                        'attack': really_complex_multi_attack_attributes.group(3)})
                    multi_attack['attacks'].append({
                        'quantity': number_string_to_number(really_complex_multi_attack_attributes.group(4)),
                        'attack': really_complex_multi_attack_attributes.group(5)})
                    monster_actions['multi_attack'] = multi_attack

    monster_data['features'] = monster_features
    monster_data['actions'] = monster_actions

    # TODO: Reactions, special things?

    # Eventually, learn the common features (legendary resistance, magic resistance, etc) and then turn them into boolean attributes for the lin reg

    return monster_data


def number_string_to_number(number_string):
    if number_string == 'one':
        return 1
    elif number_string == 'two':
        return 2
    elif number_string == 'three':
        return 3
    elif number_string == 'four':
        return 4
    elif number_string == 'five':
        return 5
    elif number_string == 'six':
        return 6
    else:
        return Exception('Unrecognized number: ' + number_string)


def get_urls_to_query(session):
    # return ['https://www.aidedd.org/dnd/monstres.php?vo=kuo-toa']
    #         'https://www.aidedd.org/dnd/monstres.php?vo=kuo-toa-archpriest',
    #         'https://www.aidedd.org/dnd/monstres.php?vo=kuo-toa-whip',
    #         'https://www.aidedd.org/dnd/monstres.php?vo=spy',
    #         'https://www.aidedd.org/dnd/monstres.php?vo=yuan-ti-pureblood']
    # Just get all of the links we can actually query from aidedd.org
    url = 'https://www.aidedd.org/dnd-filters/monsters.php'
    monster_index_html = BeautifulSoup(session.get(url).text, 'html.parser')
    urls = []
    for a_block in monster_index_html.find_all('a'):
        potential_url = a_block['href']
        if 'https://www.aidedd.org/dnd/monstres.php?vo=' in potential_url:
            urls.append(potential_url)
    return urls


if __name__ == '__main__':
    session = requests.Session()
    monster_json = []
    output_location = 'C:/Users/homel/PycharmProjects/Aboleth/monster_data.json'
    # output_location = 'C:/Users/homel/PycharmProjects/Aboleth/test_output.json'
    urls = get_urls_to_query(session)
    read_limit = 5000
    urls_read = 0
    for url in urls:
        try:
            time.sleep(0.75)
            monster_json.append(parse_monster_from_aidedd_link(session, url))
            print('Successfully read: ' + url)
            urls_read += 1
            if urls_read >= read_limit:
                break
        except:
            print('Error reading: ' + url)
            traceback.print_exc()

    print(json.dumps(monster_json, sort_keys=True, indent=4))
    with open(output_location, 'w') as output_file:
        json.dump(monster_json, output_file, sort_keys=True, indent=4)
