import math
import re



def get_expected_damage_from_dice_string(dice_string):
    dice_string_regex = r'([0-9]+)d([0-9]+) ?([\+|\-] [0-9]+)?'
    dice_result = re.search(dice_string_regex, dice_string)
    if dice_result:
        dice_multiplier = int(dice_result.group(1))
        dice_faces = int(dice_result.group(2))
        # Isn't this nuts? Conventional scope rules blanche at this!
        if dice_result.lastindex > 2:
            flat_modifier = int(dice_result.group(3).translate(str.maketrans('', '', ' +'))) # clean number; '+ 5' -> '5'
        else:
            flat_modifier = 0
        return dice_multiplier * (dice_faces + 1 / 2.0) + flat_modifier
    else:
        raise Exception('Unknown dice string  format: ' + dice_string)

# --------------------------




def convert_damage_type_lists_to_feature_array(immunity_type_list, resistance_type_list, vulnerability_type_list):
    feature_array = [1] * len(global_type_dict.keys())
    immunity_features = convert_damage_type_list_to_feature_array(immunity_type_list)
    resistance_features = convert_damage_type_list_to_feature_array(resistance_type_list)
    vulnerability_features = convert_damage_type_list_to_feature_array(vulnerability_type_list)
    for i in range(0, len(feature_array)):
        if immunity_features[i] == 1:
            feature_array[i] = 3
        elif vulnerability_features[i] == 1:
            feature_array[i] = 0
        elif resistance_features[i] == 1:
            feature_array[i] = 2
    return feature_array


def convert_damage_type_list_to_feature_array(type_list):
    feature_array = [0] * len(global_type_dict.keys())
    for damage_type in type_list:
        if damage_type == 'piercing from magic weapons wielded by good creatures':
            # This damage type is incredibly rare, so just consider it piercing from magic weapons
            damage_type = 'piercing-magical'

        if 'bludgeoning, piercing, and slashing' in damage_type:
            if '''nonmagical attacks that aren't silvered''' in damage_type \
                    or '''bludgeoning, piercing, and slashing from nonmagical attacks not made with silvered weapons''' in damage_type:
                feature_array[global_type_dict['bludgeoning-nonmagical-nonsilvered']] = 1
                feature_array[global_type_dict['piercing-nonmagical-nonsilvered']] = 1
                feature_array[global_type_dict['slashing-nonmagical-nonsilvered']] = 1
            elif '''bludgeoning, piercing, and slashing from nonmagical attacks that aren't adamantine''' in damage_type:
                feature_array[global_type_dict['bludgeoning-nonmagical-nonadamantine']] = 1
                feature_array[global_type_dict['piercing-nonmagical-nonadamantine']] = 1
                feature_array[global_type_dict['slashing-nonmagical-nonadamantine']] = 1
            elif '''bludgeoning, piercing, and slashing from nonmagical attacks''' in damage_type \
                    or 'nonmagical bludgeoning, piercing, and slashing from' in damage_type:
                feature_array[global_type_dict['bludgeoning-nonmagical']] = 1
                feature_array[global_type_dict['piercing-nonmagical']] = 1
                feature_array[global_type_dict['slashing-nonmagical']] = 1
        elif '''piercing and slashing from nonmagical attacks that aren't adamantine''' in damage_type:
            # Thanks, xorn. If stuff like this keeps happening, then parse out the types and the modifiers
            feature_array[global_type_dict['piercing-nonmagical']] = 1
            feature_array[global_type_dict['slashing-nonmagical']] = 1
        else:
            feature_array[global_type_dict[damage_type]] = 1
    return feature_array


def get_saving_throw_feature_array(monster_data):
    saving_throws = monster_data['saving_throws'].copy() if 'saving_throws' in monster_data else {}
    for attribute, value in monster_data['attributes'].items():
        if attribute not in saving_throws:
            saving_throws[attribute] = math.floor((value - 10) / 2.0)
        else:
            saving_throws[attribute] = int(saving_throws[attribute])
    return [saving_throws['str'],
            saving_throws['dex'],
            saving_throws['con'],
            saving_throws['int'],
            saving_throws['wis'],
            saving_throws['cha']]


def get_spellcasting_feature_array(monster_data):
    # TODO: What about innate spellcasting?
    spellcasting_regex = r'\(spell save DC ([0-9]+), ([+\-0-9]+) to hit'
    if 'Spellcasting' in monster_data['features']:
        spellcasting_features = re.search(spellcasting_regex, monster_data['features']['Spellcasting']['description'])
        if spellcasting_features:
            return [int(spellcasting_features.group(1)), int(spellcasting_features.group(2))]
        else:
            raise Exception('Unknown spellcasting format: ' + monster_data['features']['Spellcasting']['description'])
    elif 'Innate Spellcasting' in monster_data['features']:
        spellcasting_features = re.search(spellcasting_regex,
                                          monster_data['features']['Innate Spellcasting']['description'])
        if spellcasting_features:
            return [int(spellcasting_features.group(1)), int(spellcasting_features.group(2))]
        else:
            save_only_spellcasting_regex = r'\(spell save DC ([0-9]+)\)'
            save_only_spellcasting_features = re.search(save_only_spellcasting_regex,
                                                        monster_data['features']['Innate Spellcasting']['description'])
            if save_only_spellcasting_features:
                return [int(save_only_spellcasting_features.group(1)), 0]
            else:
                # The only thing that has trouble with this so far is the Nycanloth, whose spells have neither
                # save nor ability modifier. In this case, we want to return [0, 0], but keep printing the message
                # just in case...
                print('Unknown spellcasting format: ' + monster_data['features']['Innate Spellcasting']['description'])
                return [0, 0]
    else:
        return [0, 0]


def __get_expected_damage_from_attack(attack):
    damage = attack['expected_damage']
    if 'secondary_expected_damage' in attack:
        damage += attack['secondary_expected_damage']
    return damage

# Critical features are expected damage, to hit, damage types, probably with an array of size... 5

def get_attack_features(monster_data):
    attack_features = []
    maximum_expected_damage = 0
    if 'multi_attack' in monster_data['actions']:
        for attack in monster_data['actions']['multi_attack']['attacks']:
            if 'optional' in attack and attack['optional']:
                # print('Ignoring optional multi-attack feature: ' + str(attack))
                continue
            elif attack['attack'] in monster_data['actions']:
                expected_damage = __get_expected_damage_from_attack(monster_data['actions'][attack['attack']]) * \
                                  attack[
                                      'quantity']
                to_hit = monster_data['actions'][attack['attack']]['to_hit']
                attack_features.append([to_hit, expected_damage])
                maximum_expected_damage = max(expected_damage, maximum_expected_damage)
            elif attack['attack'].rstrip('s') in monster_data['actions']:
                attack_without_plural = attack['attack'].rstrip('s')
                expected_damage = __get_expected_damage_from_attack(monster_data['actions'][attack_without_plural]) * \
                                   attack['quantity']
                to_hit = monster_data['actions'][attack_without_plural]['to_hit']
                attack_features.append([to_hit, expected_damage])
                maximum_expected_damage = max(expected_damage, maximum_expected_damage)
            else:
                # Some stat blocks don't actually have multi-attacks that reference the actual attacks, e.g
                # animated-armor; multi-attack references melee, the actual attack is named slam. Tjuck?!
                # TODO: Fix this in harvest. For now, hack it and use the first attack type action we can find
                attacks = [x for x in monster_data['actions'].values() if x['type'] == 'attack']
                if len(attacks) == 0:
                    raise Exception('Monster has multi-attack with no attacks: ' + str(monster_data))
                elif len(attacks) >= 1:
                    expected_damage = __get_expected_damage_from_attack(attacks[0])
                    to_hit = attacks[0]['to_hit']
                    attack_features.append([to_hit, expected_damage])
                    maximum_expected_damage = max(expected_damage, maximum_expected_damage)
    else:
        # Pick the first attack for now
        for _, action in monster_data['actions'].items():
            if action['type'] == 'attack':
                expected_damage = __get_expected_damage_from_attack(action)
                to_hit = action['to_hit']
                attack_features.append([to_hit, expected_damage])
                maximum_expected_damage = max(expected_damage, maximum_expected_damage)

    while len(attack_features) < 5:
        attack_features.append([0, 0.0])
    flattened_attack_feature = [item for sublist in attack_features for item in sublist]
    return [maximum_expected_damage]


def __build_global_type_dict():
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
    type_dict = {}
    for index, damage_type in enumerate(global_type_list):
        type_dict[damage_type] = index
    return type_dict


global_type_dict = __build_global_type_dict()


def get_condition_immunity_feature_array(monster_data):
    feature_array = [0] * len(global_condition_dict.keys())
    if 'condition_immunities' in monster_data:
        for condition in monster_data['condition_immunities']:
            feature_array[global_condition_dict[condition]] = 1
    return feature_array


def __build_global_condition_dict():
    # TODO: move this to a constant
    global_condition_list = [
        'blinded',
        'charmed',
        'deafened',
        'exhaustion',
        'frightened',
        'grappled',
        'paralyzed',
        'petrified',
        'poisoned',
        'prone',
        'restrained',
        'stunned',
        'unconscious',
    ]
    condition_dict = {}
    for index, condition_type in enumerate(global_condition_list):
        condition_dict[condition_type] = index
    return condition_dict


global_condition_dict = __build_global_condition_dict()
