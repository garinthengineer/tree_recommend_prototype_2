from flask import Flask, render_template_string, request, redirect, url_for, session
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Загружаем квесты
quests_df = pd.read_csv('quests_database_with_clusters_and_descriptions.csv')

# Загружаем и подготавливаем дерево решений
tree_df = pd.read_csv('decision_tree_with_classes.csv')
tree_df['id'] = tree_df['id'].astype(int)
tree_df['left'] = pd.to_numeric(tree_df['left'], errors='coerce').astype('Int64')
tree_df['right'] = pd.to_numeric(tree_df['right'], errors='coerce').astype('Int64')
tree = {row['id']: row.to_dict() for _, row in tree_df.iterrows()}

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'current_node' not in session:
        session['current_node'] = 0
        session['history'] = []

    node_id = session['current_node']
    node = tree.get(node_id)

    if node is None:
        return f"Ошибка: узел {node_id} не найден в дереве."

    if node.get('is_leaf', False):
        # Извлекаем номер кластера как целое число из строки, например: '17 Хоррор Триллер Выживание'
        cluster_id = int(str(node['class']).split()[0])
        cluster_name = node['class']
        recommendations = (
            quests_df[quests_df['cluster_k_21'] == cluster_id]
            .sort_values(by='SORT_DEFAULT', ascending=False)
            .head(20)
        )

        return render_template_string('''
            <h2>Рекомендации: {{ class_name }}</h2>
            <p>Показаны топ-20 квестов по рейтингу SORT_DEFAULT</p>
            {% if recommendations.empty %}
                <p>Квестов по этому классу не найдено.</p>
            {% else %}
                <ul>
                {% for _, row in recommendations.iterrows() %}
                    <li><b>{{ row.QUEST }}</b> — {{ row.DESCRIPTION_SHORT }}</li>
                {% endfor %}
                </ul>
            {% endif %}
            <a href="{{ url_for('restart') }}">Начать заново</a>
        ''', class_name=cluster_name, recommendations=recommendations)

    # Обработка ответа пользователя
    if request.method == 'POST':
        answer = request.form['answer']
        session['history'].append((node_id, answer))
        try:
            next_node = int(node['left']) if answer == 'yes' else int(node['right'])
            if pd.isna(next_node):
                raise ValueError("Следующий узел отсутствует")
            session['current_node'] = next_node
            return redirect(url_for('index'))
        except Exception as e:
            return f"Ошибка при переходе к следующему узлу: {str(e)}"

    return render_template_string('''
        <h2>Вопрос: {{ feature }}?</h2>
        <form method="post">
            <button type="submit" name="answer" value="yes">Нет</button>
            <button type="submit" name="answer" value="no">Да</button>
        </form>
        <a href="{{ url_for('restart') }}">Начать заново</a>
    ''', feature=node['feature'])

@app.route('/restart')
def restart():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
    # app.run(debug=True)
