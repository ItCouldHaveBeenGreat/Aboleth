import math
import re

from monster_data_utilities import get_expected_damage_from_dice_string


class FiveEToolsJSONWrapper:
    def __init__(self, json_data):
        self.json_data = json_data

    def has_challenge_rating(self):
        return 'cr' in self.json_data and self.json_data['cr'] != 'Unknown'

    def is_copy(self):
        # TODO: Currently we don't support parsing copies
        # Find some way to inject the base monster (and add that logic to a layer above)
        return '_copy' in self.json_data

    def armor_class(self):
        highest_ac = 0
        for ac_entry in self.json_data['ac']:
            if isinstance(ac_entry, int):
                highest_ac = max(highest_ac, ac_entry)
            elif isinstance(ac_entry, dict):
                if 'ac' in ac_entry:
                    highest_ac = max(highest_ac, ac_entry['ac'])
            else:
                raise Exception('Unrecognized armor class entry: ' + str(ac_entry))
        return highest_ac

    def hp(self):
        return self.json_data['hp']['average']

    def name(self):
        return self.json_data['name']

    def attributes(self):
        return [self.attribute('str'),
                self.attribute('dex'),
                self.attribute('con'),
                self.attribute('int'),
                self.attribute('wis'),
                self.attribute('cha')]

    # attribute = ['str', 'dex', 'con', 'int', 'wis', 'cha']
    def attribute(self, attribute):
        return self.json_data[attribute]

    def saves(self):
        return [self.save('str'),
                self.save('dex'),
                self.save('con'),
                self.save('int'),
                self.save('wis'),
                self.save('cha')]

    # attribute = ['str', 'dex', 'con', 'int', 'wis', 'cha']
    def save(self, attribute):
        if 'save' in self.json_data:
            if attribute in self.json_data['save']:
                save_string = self.json_data['save'][attribute]
                if save_string[0] == '+':
                    return int(save_string[1:])
                elif save_string[0] == '-':
                    return int(save_string)
                else:
                    raise Exception('Unrecognized save format: ' + save_string)
        # Otherwise, derive save from base attributes
        return math.floor((self.attribute(attribute) - 10) / 2.0)

    def challenge_rating(self):
        cr_entry = self.json_data['cr']
        if isinstance(cr_entry, str):
            cr_text = cr_entry
        elif isinstance(cr_entry, dict):
            # See Bheur Hag entry
            cr_text = cr_entry['cr']
        else:
            raise Exception('Unknown challenge rating entry: ' + str(cr_entry))

        if '/' in cr_text:
            fraction_parts = cr_text.split('/')
            return float(fraction_parts[0]) / float(fraction_parts[1])
        else:
            return float(cr_text)

    def get_spellcasting_dc(self):
        return self.__get_spellcasting_feature(r'{@dc ([0-9]+)}')

    def get_spellcasting_to_hit(self):
        return self.__get_spellcasting_feature(r'{@hit ([0-9]+)}')

    def get_spellcasting_level(self):
        return self.__get_spellcasting_feature(r'([0-9]+)(nd|rd|th)-level spellcaster')

    def __get_spellcasting_feature(self, regex):
        feature_value = 0
        if 'spellcasting' in self.json_data:
            for spellcasting in self.json_data['spellcasting']:
                spellcasting_string = str(spellcasting['headerEntries'])
                spellcasting_feature = re.search(regex, spellcasting_string)
                if spellcasting_feature:
                    feature_value = int(spellcasting_feature.group(1))
        return feature_value

    def get_traits(self):
        if 'traitTags' in self.json_data:
            return self.json_data['traitTags']
        else:
            return []

    def get_features_array(monster_data):
        features = [
            monster_data.armor_class(),
            monster_data.hp(),
            monster_data.get_spellcasting_to_hit(),
            monster_data.get_spellcasting_dc()
        ]
        features += monster_data.saves()
        features += monster_data.__get_traits_array()
        monster_data.get_damage_from_attacks()


        return features

    def __get_traits_array(self):
        traits = self.get_traits()
        feature_array = [0] * 6 # Not all features help; reducing the size of this array appears to make things better
        if 'Legendary Resistances' in traits:
            feature_array[0] = 1
        if 'Magic Resistance' in traits:
            feature_array[1] = 1
        if 'Pack Tactics' in traits:
            feature_array[2] = 1
        if 'Regeneration' in traits:
            feature_array[3] = 1
        if 'Pack Tactics' in traits:
            feature_array[4] = 1
        if 'Fey Ancestry' in traits:
            feature_array[5] = 1 # Consider reduction!!
        return feature_array

    def get_damage_from_attacks(self):
        # What kind of creature has no actions? The super cool 'Guardian Portrait'!
        if 'action' not in self.json_data:
            return 0

        # Get all attacks we actually understand
        for action in self.json_data['action']:
            attack_features = self.__get_attack_features(action)

        if 'actionTags' in self.json_data and 'Multiattack' in self.json_data['actionTags']:
            # Determine the kinds of attacks we're looking at
            return

    def __get_attack_features(self, attack_entry):
        attack_features = {}
        attack_features['name'] = attack_entry['name']

        #if len(attack_entry['entries']) > 1:
        #    print('Found an attack entry with multiple elements: ' + str(attack_entry))

        to_hit_regex = r'{@hit ([0-9]+)}'
        to_hit_result = re.search(to_hit_regex, attack_entry['entries'][0])
        if to_hit_result:
            attack_features['to_hit'] = int(to_hit_result.group(1))

        attack_type_regex = r'{@atk ([A-z]+)}'
        attack_type_result = re.search(attack_type_regex, attack_entry['entries'][0])
        if attack_type_result:
            attack_features['type'] = attack_type_result.group(1)

        reach_regex = r'reach ([0-9]+)/?([0-9]+)? ft\.,'
        reach_result = re.search(reach_regex, attack_entry['entries'][0])
        if reach_result:
            attack_features['range'] = int(reach_result.group(1)) # Just ignore the range with disadvantage

        # Note: The 'takes' clause literally only exists for the Fire Giant Dreadnought, for an action that isn't even
        # an attack, so the or clause doesn't blow up. Probably should get rid of it from the regex, this is a dirty
        # hack!
        damage_regex = r'(takes|or|plus|\{\@h\}) ?([0-9]+) ?(?:\(\{@damage ([d0-9\+\- ]+)\}(?: plus \{@damage ([d0-9\+\- ]+)\})?\))? ([A-z]+)? ?damage'
        damage_results = re.findall(damage_regex, attack_entry['entries'][0])
        if damage_results:
            damage_entries = []
            for damage_result in damage_results:
                clause = damage_result[0]
                if damage_result[2]:  # There is a damage dice string; use that!
                    expected_damage = get_expected_damage_from_dice_string(damage_result[2])
                else: # Default to the stated damage otherwise
                    expected_damage = int(damage_result[1])
                if damage_result[3]: # There is a secondary damage dice string; add it!
                    expected_damage = expected_damage + get_expected_damage_from_dice_string(damage_result[3])
                damage_entry = {
                    'expected_damage': expected_damage,
                    'damage_type': damage_result[4]
                }
                # If clause is 'or' and the expected damage is higher than the previous entry, replace previous entry
                # e.g: 14 ({@damage 2d6 + 7}) slashing damage, or 17 ({@damage 2d6 + 10}) slashing damage while raging
                if clause == 'or':
                    if len(damage_entries) == 0:
                        raise Exception('An attack damage entry has an or clause with no preceding entry: ' + attack_entry['entries'][0])
                    if damage_entries[-1]['expected_damage'] > damage_entry['expected_damage']:
                        damage_entries[-1] = damage_entry
                else:
                    damage_entries.append(damage_entry)
            attack_features['damage_entries'] = damage_entries
        return attack_features


