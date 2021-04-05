# from sklearn.linear_model import LinearRegression
from matplotlib import pyplot as plt
import json
import sys
import time
import traceback
# from joblib import dump, load

from sklearn.neural_network import MLPRegressor

from monster_data_utilities import get_special_feature_array, get_saving_throw_feature_array, \
    convert_damage_type_lists_to_feature_array, get_spellcasting_feature_array, get_condition_immunity_feature_array, \
    get_damage_per_round


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
    features += get_saving_throw_feature_array(monster_data)
    features += convert_damage_type_lists_to_feature_array(
        monster_data['damage_immunities'] if 'damage_immunities' in monster_data else [],
        monster_data['damage_resistances'] if 'damage_resistances' in monster_data else [],
        monster_data['damage_vulnerabilities'] if 'damage_vulnerabilities' in monster_data else [])
    features += get_spellcasting_feature_array(monster_data)
    features += get_special_feature_array(monster_data)
    features += get_condition_immunity_feature_array(monster_data)
    return features


def get_monster_cr(monster_data):
    return monster_data['challenge']


def get_monster_name(monster_data):
    return monster_data['name']


def fit_to_data(training_monster_data):
    monster_features = []
    monster_crs = []
    for monster_datum in training_monster_data:
        try:
            monster_features.append(get_monster_features(monster_datum))
            monster_crs.append(get_monster_cr(monster_datum))
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print('Failed to parse: ' + str(monster_datum))
            print('Reason: ' + str(exc_type) + ', ' + str(e))
            traceback.print_exc()

    regressor = MLPRegressor(max_iter=800, random_state=42).fit(monster_features, monster_crs)
    # regressor = LinearRegression().fit(monster_features, monster_crs)
    print(regressor.score(monster_features, monster_crs))
    return regressor


def render_data(regressor, monster_data):
    monster_features = []
    monster_crs = []
    monster_names = []
    for monster_datum in monster_data:
        try:
            monster_features.append(get_monster_features(monster_datum))
            monster_crs.append(get_monster_cr(monster_datum))
            monster_names.append(get_monster_name(monster_datum))
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print('Failed to parse: ' + str(monster_datum))
            print('Reason: ' + str(exc_type) + ', ' + str(e))
            traceback.print_exc()

    cr_predictions = regressor.predict(monster_features)
    monster_crs_errors = cr_predictions - monster_crs

    # Plot everything useful!
    fig, ax = plt.subplots(nrows=3, ncols=1, figsize=(10, 20))
    render_prediction_accuracy(ax[0], monster_names, monster_crs, monster_crs_errors)
    render_cr_to_health(ax[1], monster_data)
    render_cr_to_damage(ax[2], monster_data)
    plt.show()


def render_prediction_accuracy(ax, monster_names, monster_crs, monster_crs_errors):
    ax.scatter(monster_crs, monster_crs_errors, s=1, color='black')

    CLOSE_ENOUGH_FACTOR = 0.05
    for i in range(0, len(monster_names)):
        error_percent = monster_crs_errors[i] / monster_crs[i] if monster_crs[i] > 0 else monster_crs_errors[i]
        color = 'black'
        if error_percent < -CLOSE_ENOUGH_FACTOR:
            color = 'blue'
        elif error_percent > CLOSE_ENOUGH_FACTOR:
            color = 'red'
        ax.annotate(monster_names[i], (monster_crs[i], monster_crs_errors[i]), color=color, fontsize=6)

    ax.set_title('Prediction Accuracy')
    ax.set_xlabel('cr actual')
    ax.set_ylabel('cr prediction - cr actual')


def render_cr_to_health(ax, monster_data):
    monster_crs = []
    monster_health = []
    monster_names = []
    for monster_datum in monster_data:
        monster_crs.append(monster_datum['challenge'])
        monster_health.append(monster_datum['hit_points'])
        monster_names.append(monster_datum['name'])

    ax.scatter(monster_crs, monster_health, s=1, color='black')
    for i in range(0, len(monster_data)):
        ax.annotate(monster_names[i], (monster_crs[i], monster_health[i]), color='black', fontsize=6)
    ax.set_title('CR to Health')
    ax.set_xlabel('cr')
    ax.set_ylabel('health')


def render_cr_to_damage(ax, monster_data):
    monster_crs = []
    monster_damage = []
    monster_names = []
    for monster_datum in monster_data:
        try:
            monster_damage.append(get_damage_per_round(monster_datum))
            monster_crs.append(monster_datum['challenge'])
            monster_names.append(monster_datum['name'])
        except:
            print('Ignoring ' + monster_datum['name'] + ' because damage could not be got!')

    ax.scatter(monster_crs, monster_damage, s=1, color='black')
    for i in range(0, len(monster_crs)):
        ax.annotate(monster_names[i], (monster_crs[i], monster_damage[i]), color='black', fontsize=6)
    ax.set_title('CR to Damage')
    ax.set_xlabel('cr')
    ax.set_ylabel('damage')


def run_train_render_evaluate(monster_data_location, monster_data_to_evaluate_location):
    with open(monster_data_location, 'r') as monster_data_file:
        monster_data = json.load(monster_data_file)
        # TODO: Eventually, consider a train test split.
        # X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=1)
        regressor = fit_to_data(monster_data)
        render_data(regressor, monster_data)

        monster_data_to_score = ''
        potential_monster_data_to_score = ''
        while (True):
            with open(monster_data_to_evaluate_location, 'r') as monster_data_to_score_file:
                try:
                    potential_monster_data_to_score = json.load(monster_data_to_score_file)
                except:
                    print("Invalid JSON!")
                if potential_monster_data_to_score != monster_data_to_score:
                    monster_data_to_score = potential_monster_data_to_score
                    features = [get_monster_features(monster_data_to_score)]
                    print('Predicted CR: ' + str(regressor.predict(features)))
            time.sleep(2)


if __name__ == '__main__':
    monster_data_location = 'monster_data.json'
    monster_data_to_evaluate_location = 'evaluate.json'
    run_train_render_evaluate(monster_data_location, monster_data_to_evaluate_location)
