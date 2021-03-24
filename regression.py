from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from matplotlib import pyplot as plt
import numpy as np
import json


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

def get_monster_features(monster_data):
    return [
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

    for i in range(0, len(monster_names)):
        color = 'blue' if cr_predictions[i] < monster_crs[i] else 'red'
        if monster_crs[i] == cr_predictions[i]:
            color = 'black'
        ax.annotate(monster_names[i], (monster_crs[i], monster_crs_errors[i]), color=color)

    plt.show()

if __name__ == '__main__':
    monster_data_location = 'test_output.json'
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
                print('Failed to parse: ' + str(monster_datum))
                print('Reason: ' + str(e))

    fit_to_data(monster_features, monster_crs, monster_names)
