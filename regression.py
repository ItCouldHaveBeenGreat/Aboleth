
from sklearn.linear_model import LinearRegression
from matplotlib import pyplot as plt
import json
import re
import sys
import traceback

def get_spellcasting_feature_array(monster_data):
    # Spellcasting. The drow is a 10th-level spellcaster. Its spellcasting ability is Intelligence (spell save DC 14, +6 to hit with spell attacks). The drow has the following wizard spells prepared:

    # What about innate spellcasting?
    spellcasting_regex = '\(spell save DC ([0-9]+), ([+\-0-9]+) to hit'
    if 'Spellcasting' in monster_data['features']:
        spellcasting_features = re.search(spellcasting_regex, monster_data['features']['Spellcasting'])
        if spellcasting_features:
            return [int(spellcasting_features.group(1)), int(spellcasting_features.group(2))]
        else:
            raise Exception('Unknown spellcasting format: ' + monster_data['features']['Spellcasting'])
    else:
        return [0, 0]


def get_damage_per_round(monster_data):
    if 'multi_attack' in monster_data['actions']:
        expected_damage = 0
        for attack in monster_data['actions']['multi_attack']['attacks']:
            if 'optional' in attack and attack['optional'] == True:
                print('Ignoring optional feature: ' + str(attack))
                continue
            elif attack['attack'] in monster_data['actions']:
                expected_damage += monster_data['actions'][attack['attack']]['expected_damage'] * attack['quantity']
            elif attack['attack'].rstrip('s') in monster_data['actions']:
                attack_without_plural = attack['attack'].rstrip('s')
                expected_damage += monster_data['actions'][attack_without_plural]['expected_damage'] * attack['quantity']
            else:
                # Some stat blocks don't actually have multi-attacks that reference the actual attacks, e.g
                # animated-armor; multi-attack references melee, the actual attack is named slam. Tjuck?!
                # TODO: Fix this in harvest. For now, hack it and use the first attack type action we can find
                attacks = [x for x in  monster_data['actions'].values() if x['type'] == 'attack']
                if len(attacks) == 0:
                    raise Exception('Monster has multi-attack with no attacks: ' + str(monster_data))
                elif len(attacks) == 1:
                    expected_damage += attacks[0]['expected_damage']
                elif len(attacks) > 1:
                    raise Exception('Monster has ambiguous multi-attack: ' + str(monster_data))
        return expected_damage
    else:
        expected_damage = 0
        for attack_name, attack_block in monster_data['actions'].items():
            expected_damage = max(expected_damage, attack_block['expected_damage'])
        return expected_damage


def build_global_type_dict():
    # TODO: move this to a constant
    global_type_list = [
        'acid',
        'bludgeoning',
        'bludgeoning-nonmagical',
        'bludgeoning-nonmagical-nonsilvered',
        'bludgeoning-nonmagical-nonadamantine',
        'cold',
        'damage from spells',
        'fire',
        'force',
        'lightning',
        'necrotic',
        'piercing',
        'piercing-nonmagical',
        'piercing-magical',
        'piercing-nonmagical-nonsilvered',
        'piercing-nonmagical-nonadamantine',
        'poison',
        'psychic',
        'radiant',
        'slashing',
        'slashing-nonmagical',
        'slashing-nonmagical-nonsilvered',
        'slashing-nonmagical-nonadamantine',
        'thunder',
    ]
    global_type_dict = {}
    for index, type in enumerate(global_type_list):
        global_type_dict[type] = index
    return global_type_dict

global_type_dict = build_global_type_dict()
def convert_damage_type_list_to_feature_array(type_list):
    feature_array = [0] * len(global_type_dict.keys())
    for type in type_list:
        if type == 'piercing from magic weapons wielded by good creatures':
            # This damage type is incredibly rare, so just consider it piercing from magic weapons
            type = 'piercing-magical'

        if 'bludgeoning, piercing, and slashing' in type:
            if '''nonmagical attacks that aren't silvered''' in type \
                    or '''bludgeoning, piercing, and slashing from nonmagical attacks not made with silvered weapons''' in type:
                feature_array[global_type_dict['bludgeoning-nonmagical-nonsilvered']] = 1
                feature_array[global_type_dict['piercing-nonmagical-nonsilvered']] = 1
                feature_array[global_type_dict['slashing-nonmagical-nonsilvered']] = 1
            elif '''bludgeoning, piercing, and slashing from nonmagical attacks that aren't adamantine''' in type:
                feature_array[global_type_dict['bludgeoning-nonmagical-nonadamantine']] = 1
                feature_array[global_type_dict['piercing-nonmagical-nonadamantine']] = 1
                feature_array[global_type_dict['slashing-nonmagical-nonadamantine']] = 1
            elif '''bludgeoning, piercing, and slashing from nonmagical attacks''' in type \
                    or 'nonmagical bludgeoning, piercing, and slashing from' in type:
                feature_array[global_type_dict['bludgeoning-nonmagical']] = 1
                feature_array[global_type_dict['piercing-nonmagical']] = 1
                feature_array[global_type_dict['slashing-nonmagical']] = 1
        elif '''piercing and slashing from nonmagical attacks that aren't adamantine'''  in type:
            # Thanks, xorn. If stuff like this keeps happening, then parse out the types and the modifiers
            feature_array[global_type_dict['piercing-nonmagical']] = 1
            feature_array[global_type_dict['slashing-nonmagical']] = 1
        else:
            feature_array[global_type_dict[type]] = 1
    return feature_array

def get_monster_features(monster_data):
    features = [
        get_damage_per_round(monster_data),
        monster_data['armor_class'],
        monster_data['attributes']['cha'],
        monster_data['attributes']['con'],
        monster_data['attributes']['dex'],
        monster_data['attributes']['int'],
        monster_data['attributes']['str'],
        monster_data['attributes']['wis'],
        monster_data['hit_points']
    ]
    features += convert_damage_type_list_to_feature_array(monster_data['damage_immunities'] if 'damage_immunities' in monster_data else [])
    features += convert_damage_type_list_to_feature_array(monster_data['damage_resistances'] if 'damage_resistances' in monster_data else [])
    features += convert_damage_type_list_to_feature_array(monster_data['damage_vulnerabilities'] if 'damage_vulnerabilities' in monster_data else [])
    return features

def get_monster_cr(monster_data):
    return monster_data['challenge']

def get_monster_name(monster_data):
    return monster_data['name']

def fit_to_data(monster_features, monster_crs, monster_names):
    reg = LinearRegression().fit(monster_features, monster_crs)
    cr_predictions = reg.predict(monster_features)
    monster_crs_errors = cr_predictions - monster_crs

    print(reg.score(monster_features, monster_crs))

    # Plot outputs
    fig, ax = plt.subplots()
    ax.scatter(monster_crs, monster_crs_errors, color='black')
    #ax.plot(range(0, 30))

    CLOSE_ENOUGH_FACTOR = 0.99
    for i in range(0, len(monster_names)):
        color = 'blue' if cr_predictions[i] < monster_crs[i] else 'red'
        if monster_crs[i] > cr_predictions[i] * CLOSE_ENOUGH_FACTOR and monster_crs[i] < cr_predictions[i] / CLOSE_ENOUGH_FACTOR:
            color = 'black'
        ax.annotate(monster_names[i], (monster_crs[i], monster_crs_errors[i]), color=color)

    plt.show()

if __name__ == '__main__':
    monster_data_location = 'monster_data.json'
    with open(monster_data_location, 'r') as monster_data_file:
        monster_data = json.load(monster_data_file)
        monster_features = []
        monster_crs = []
        monster_names = []
        for monster_datum in monster_data:
            try :
                monster_features.append(get_monster_features(monster_datum))
                monster_crs.append(get_monster_cr(monster_datum))
                monster_names.append(get_monster_name(monster_datum))

                #print(get_monster_name(monster_datum) + ": " + str(get_monster_features(monster_datum)) + ": " + str(get_monster_cr(monster_datum)))
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                print('Failed to parse: ' + str(monster_datum))
                print('Reason: ' + str(exc_type) + ', ' + str(e))
                traceback.print_exc()

    fit_to_data(monster_features, monster_crs, monster_names)
