import json
import sys
import time
import traceback

from sklearn.neural_network import MLPRegressor
from five_e_tools_json_wrapper import FiveEToolsJSONWrapper


def fit_to_data(training_monster_data):
    # TODO: Eventually, consider a train test split. X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=1)
    monster_features = []
    monster_crs = []
    for monster_datum in training_monster_data:
        try:
            if monster_datum.challenge_rating() > 0:
                monster_features.append(monster_datum.get_features_array())
                monster_crs.append(monster_datum.challenge_rating())
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print('Failed to parse: ' + str(monster_datum.json_data))
            print('Reason: ' + str(exc_type) + ', ' + str(e))
            traceback.print_exc()

    print("Final Training Data Size: " + str(len(monster_features)))
    regressor = MLPRegressor(max_iter=100000,
                             alpha=0.01,
                             random_state=42,
                             early_stopping=True).fit(monster_features, monster_crs)
    #regressor = LinearRegression().fit(monster_features, monster_crs)
    #regressor = RandomForestRegressor().fit(monster_features, monster_crs)
    print("Regressor Score: " + str(regressor.score(monster_features, monster_crs)))
    return regressor


def parse_monster_data_from_file(monster_data_location):
    print('Loading training data from file: ' + str(monster_data_location))
    with open(monster_data_location, 'r') as monster_data_file:
        raw_monster_data = json.load(monster_data_file)
        print('Raw Training Data Size: ' + str(len(raw_monster_data)))

        monster_data = []
        for raw_monster_datum in raw_monster_data:
            monster_datum = FiveEToolsJSONWrapper(raw_monster_datum)
            # We only want to include monsters with a challenge rating
            # TODO: Currently we don't (but could) load copies. These are actually the most
            # TODO: interesting monsters because they have a built-in diff.
            if monster_datum.has_challenge_rating() and not monster_datum.is_copy():
                monster_data.append(monster_datum)
        print('Parsed Training Data Size: ' + str(len(monster_data)))
        return monster_data


def repeatedly_evaluate_data_from_file(regressor, monster_data_to_evaluate_location):
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
                features = monster_data_to_score.get_features_array()
                print('Features: ' + str(features))
                print('Predicted CR: ' + str(regressor.predict(features)))
        time.sleep(2)


if __name__ == '__main__':
    monster_data_location = '5etools_data/beastiary.json'
    monster_data_to_evaluate_location = 'evaluate.json'

    monster_data = parse_monster_data_from_file(monster_data_location)
    regressor = fit_to_data(monster_data)
    #render_data(regressor, monster_data)
    #repeatedly_evaluate_data_from_file(regressor, monster_data_to_evaluate_location)
