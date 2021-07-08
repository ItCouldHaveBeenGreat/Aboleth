from matplotlib import pyplot as plt
import traceback

# TODO: All of this needs to be updated to use the 5etoolsjsonwrapper
def render_data(regressor, monster_data):
    monster_features = []
    monster_crs = []
    monster_names = []
    for monster_datum in monster_data:
        try:
            monster_features.append(monster_datum.get_features_array())
            monster_crs.append(monster_datum.challenge_rating())
            monster_names.append(monster_datum.name())
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print('Failed to parse: ' + str(monster_datum))
            print('Reason: ' + str(exc_type) + ', ' + str(e))
            traceback.print_exc()

    cr_predictions = regressor.predict(monster_features)
    monster_crs_errors = cr_predictions - monster_crs
    score = regressor.score(monster_features, monster_crs)

    # Plot everything useful!
    fig, ax = plt.subplots(nrows=3, ncols=1, figsize=(10, 20))
    render_prediction_accuracy(ax[0], monster_names, monster_crs, monster_crs_errors)
    render_cr_to_health(ax[1], monster_data)
    render_cr_to_damage(ax[2], monster_data)
    plt.title(str(score))
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
            # TODO: Fix this to use get_attack_features
            monster_damage.append(0)
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