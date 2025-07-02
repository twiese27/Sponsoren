from flask import Blueprint, render_template_string, request, redirect, url_for, session, jsonify, flash
from db import get_db_connection, get_current_user
import math

sponsoren_bp = Blueprint('sponsoren', __name__)

PER_PAGE_CHOICES = [10, 25, 50, 100, 500]

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Sponsorenliste</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        form { margin-bottom: 25px; background: #f8f8f8; padding: 15px 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.03);}
        form .form-row { margin-bottom: 10px; }
        form label { display: inline-block; width: 120px; font-weight: bold; }
        form input[type=text], form textarea { width: 250px; padding: 4px; border: 1px solid #ccc; border-radius: 3px; }
        form textarea { height: 40px; resize: vertical; }
        form input[type=submit], button { padding: 6px 18px; background: #4CAF50; color: #fff; border: none; border-radius: 3px; cursor: pointer; }
        form input[type=submit]:hover, button:hover { background: #388e3c; }
        .legend { margin-bottom: 15px; font-size: 14px; }
        .legend .color-box { display: inline-block; width: 20px; height: 20px; background-color: #ffcccc; border: 1px solid #cc0000; vertical-align: middle; margin-right: 8px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
        thead th { position: sticky; top: 0; background-color: #f2f2f2; z-index: 10; box-shadow: 0 2px 2px -1px rgba(0,0,0,0.4);}
        tr.nie-mehr-anfragen { background-color: #ffcccc; }
        tr.nicht-validiert { background-color: #e3f2fd; }
        .pagination { margin: 20px 0; text-align: center; }
        .pagination a, .pagination span { display: inline-block; padding: 6px 12px; margin: 0 2px; border: 1px solid #ccc; border-radius: 3px; text-decoration: none; color: #333; }
        .pagination .current { background: #4CAF50; color: #fff; border-color: #388e3c; }
        .per-page-form { display: inline-block; margin: 0 15px; }
        td.editing { background: #ffe; }
        input[type="radio"] { margin-left: 10px; margin-right: 2px; }
        .userbox {
            position: absolute;
            top: 20px;
            right: 30px;
            background: #f8f8f8;
            padding: 7px 14px;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.07);
            font-size: 15px;
            z-index: 100;
        }
        @media (max-width: 700px) {
            .userbox {
                position: static;
                float: none;
                margin: 10px 0;
                display: block;
                width: auto;
                box-shadow: none;
            }
        }
    </style>
    <script>
    document.addEventListener('DOMContentLoaded', () => {
        const boolFields = ['angefragt', 'rueckmeldung', 'sponsor_ja_nein'];

        function createInput(cell, field, currentValue, sponsorId) {
            if (cell.classList.contains('editing')) return;
            cell.classList.add('editing');
            cell.innerHTML = '';

            if (boolFields.includes(field)) {
                // Radio buttons für boolean
                const yesId = `yes_${field}_${sponsorId}`;
                const noId = `no_${field}_${sponsorId}`;

                const yesLabel = document.createElement('label');
                yesLabel.htmlFor = yesId;
                yesLabel.textContent = 'Ja';

                const noLabel = document.createElement('label');
                noLabel.htmlFor = noId;
                noLabel.textContent = 'Nein';

                const yesRadio = document.createElement('input');
                yesRadio.type = 'radio';
                yesRadio.name = field + sponsorId;
                yesRadio.id = yesId;
                yesRadio.value = '1';
                if (currentValue === 'Ja' || currentValue === '1' || currentValue === 1) yesRadio.checked = true;

                const noRadio = document.createElement('input');
                noRadio.type = 'radio';
                noRadio.name = field + sponsorId;
                noRadio.id = noId;
                noRadio.value = '0';
                if (currentValue === 'Nein' || currentValue === '0' || currentValue === 0) noRadio.checked = true;

                cell.appendChild(yesRadio);
                cell.appendChild(yesLabel);
                cell.appendChild(noRadio);
                cell.appendChild(noLabel);

                yesRadio.addEventListener('change', () => saveEdit(sponsorId, field, yesRadio.value, cell));
                noRadio.addEventListener('change', () => saveEdit(sponsorId, field, noRadio.value, cell));
            } else {
                // Textinput für andere Felder
                const input = document.createElement('input');
                input.type = 'text';
                input.value = currentValue;
                input.style.width = '95%';
                cell.appendChild(input);
                input.focus();

                input.addEventListener('blur', () => {
                    saveEdit(sponsorId, field, input.value, cell);
                });
                input.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        input.blur();
                    }
                    if (e.key === 'Escape') {
                        cell.textContent = currentValue;
                        cell.classList.remove('editing');
                    }
                });
            }
        }

        async function saveEdit(sponsorId, field, value, cell) {
            const response = await fetch('/edit', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({id: sponsorId, field: field, value: value})
            });
            if (response.ok) {
                if (['angefragt', 'rueckmeldung', 'sponsor_ja_nein'].includes(field)) {
                    cell.textContent = (value === '1' || value === 1) ? 'Ja' : 'Nein';
                } else {
                    cell.textContent = value;
                }
            } else {
                alert('Fehler beim Speichern!');
                cell.textContent = value;
            }
            cell.classList.remove('editing');
        }

        // Doppelklick-Listener auf alle editierbaren Zellen
        document.querySelectorAll('td[data-field]').forEach(cell => {
            cell.addEventListener('dblclick', () => {
                const sponsorId = cell.closest('tr').dataset.id;
                const field = cell.dataset.field;
                const currentValue = cell.textContent.trim();
                createInput(cell, field, currentValue, sponsorId);
            });
        });
    });
    </script>
</head>
<body>
    <div class="userbox">
        {% if current_user %}
            Eingeloggt als: <b>{{ current_user['vorname'] }} {{ current_user['nachname'] }}</b> ({{ current_user['rolle'] }}) |
            <a href="{{ url_for('login.logout') }}">Logout</a>
        {% endif %}
    </div>
    <h1>Sponsorenverwaltung</h1>

    <!-- Eingabeformular -->
    <form method="post">
        <div class="form-row">
            <label for="name">Name:</label>
            <input type="text" id="name" name="name" required>
            <label for="adresse">Adresse:</label>
            <input type="text" id="adresse" name="adresse" required>
        </div>
        <div class="form-row">
            <label for="emails">Mailadressen (Komma getrennt):</label>
            <input type="text" id="emails" name="emails">
        </div>
        <div class="form-row">
            <label for="wichtig">Wichtig:</label>
            <input type="text" id="wichtig" name="wichtig">
            <label for="angefragt">Angefragt:</label>
            <input type="text" id="angefragt" name="angefragt">
            <label for="rueckmeldung">Rückmeldung:</label>
            <input type="text" id="rueckmeldung" name="rueckmeldung">
        </div>
        <div class="form-row">
            <label for="sponsor_ja_nein">Sponsor Ja/Nein:</label>
            <input type="text" id="sponsor_ja_nein" name="sponsor_ja_nein">
            <label for="gegenleistung">Gegenleistung:</label>
            <input type="text" id="gegenleistung" name="gegenleistung">
        </div>
        <div class="form-row">
            <label for="was">Was:</label>
            <input type="text" id="was" name="was">
            <label for="sponsoring_2024">Sponsoring 2024:</label>
            <input type="text" id="sponsoring_2024" name="sponsoring_2024">
        </div>
        <input type="submit" value="Hinzufügen">
    </form>

    <!-- Legende -->
    <div class="legend">
        <span class="color-box"></span>
        Sponsoren wurden angefragt und haben weder jetzt noch in Zukunft Interesse an einem Sponsoring.
        <span style="display:inline-block; width:20px; height:20px; background:#e3f2fd; border:1px solid #90caf9; margin-left:20px; vertical-align:middle;"></span>
        Noch nicht validierte Sponsoren
    </div>

    <!-- Filterformular -->
    <form method="get" style="margin-bottom: 20px;">
        <input type="text" name="search" placeholder="Nach Name suchen..." value="{{ search|default('') }}">
        <label style="margin-left:15px;">Angefragt:
            <select name="f_angefragt">
                <option value="">Alle</option>
                <option value="1" {% if f_angefragt == '1' %}selected{% endif %}>Ja</option>
                <option value="0" {% if f_angefragt == '0' %}selected{% endif %}>Nein</option>
            </select>
        </label>
        <label style="margin-left:10px;">Rückmeldung:
            <select name="f_rueckmeldung">
                <option value="">Alle</option>
                <option value="1" {% if f_rueckmeldung == '1' %}selected{% endif %}>Ja</option>
                <option value="0" {% if f_rueckmeldung == '0' %}selected{% endif %}>Nein</option>
            </select>
        </label>
        <label style="margin-left:10px;">Sponsor Ja/Nein:
            <select name="f_sponsor_ja_nein">
                <option value="">Alle</option>
                <option value="1" {% if f_sponsor_ja_nein == '1' %}selected{% endif %}>Ja</option>
                <option value="0" {% if f_sponsor_ja_nein == '0' %}selected{% endif %}>Nein</option>
            </select>
        </label>
        <label style="margin-left:10px;">Validiert:
            <select name="f_validiert">
                <option value="">Alle</option>
                <option value="1" {% if f_validiert == '1' %}selected{% endif %}>Ja</option>
                <option value="0" {% if f_validiert == '0' %}selected{% endif %}>Nein</option>
            </select>
        </label>
        <input type="hidden" name="per_page" value="{{ per_page }}">
        <button type="submit">Filtern</button>
    </form>

    <!-- Pagination und Per-Page Auswahl oben -->
    <div class="pagination">
        <form method="get" class="per-page-form" style="display:inline;">
            <label for="per_page_top">Zeilen pro Seite:</label>
            <select name="per_page" id="per_page_top" onchange="this.form.submit()">
                {% for val in per_page_choices %}
                    <option value="{{val}}" {% if val == per_page %}selected{% endif %}>{{val}}</option>
                {% endfor %}
            </select>
            <input type="hidden" name="page" value="1">
            {% if search %}<input type="hidden" name="search" value="{{ search }}">{% endif %}
            {% if f_angefragt %}<input type="hidden" name="f_angefragt" value="{{ f_angefragt }}">{% endif %}
            {% if f_rueckmeldung %}<input type="hidden" name="f_rueckmeldung" value="{{ f_rueckmeldung }}">{% endif %}
            {% if f_sponsor_ja_nein %}<input type="hidden" name="f_sponsor_ja_nein" value="{{ f_sponsor_ja_nein }}">{% endif %}
            {% if f_validiert %}<input type="hidden" name="f_validiert" value="{{ f_validiert }}">{% endif %}
        </form>
        {% for p in range(1, total_pages+1) %}
            {% if p == page %}
                <span class="current">{{p}}</span>
            {% else %}
                <a href="?page={{p}}&per_page={{per_page}}{% if search %}&search={{ search }}{% endif %}{% if f_angefragt %}&f_angefragt={{ f_angefragt }}{% endif %}{% if f_rueckmeldung %}&f_rueckmeldung={{ f_rueckmeldung }}{% endif %}{% if f_sponsor_ja_nein %}&f_sponsor_ja_nein={{ f_sponsor_ja_nein }}{% endif %}{% if f_validiert %}&f_validiert={{ f_validiert }}{% endif %}">{{p}}</a>
            {% endif %}
        {% endfor %}
    </div>

    <!-- Tabelle -->
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Adresse</th>
                <th>Wichtig</th>
                <th>Angefragt</th>
                <th>Rückmeldung</th>
                <th>Sponsor Ja/Nein</th>
                <th>Zusätzliche Info</th>
                <th>Gegenleistung</th>
                <th>Was</th>
                <th>Sponsoring 2024</th>
                <th>Validiert</th>
            </tr>
        </thead>
        <tbody>
            {% for sponsor in sponsoren %}
            <tr data-id="{{ sponsor.id }}"
                class="{% if sponsor.nie_mehr_anfragen %}nie-mehr-anfragen{% endif %} {% if not sponsor.validiert %}nicht-validiert{% endif %}">
                <td>{{ sponsor.id }}</td>
                <td data-field="name">{{ sponsor.name }}</td>
                <td data-field="adresse">{{ sponsor.adresse | replace('\n', '<br>') | safe }}</td>
                <td data-field="wichtig">{{ sponsor.wichtig }}</td>
                <td data-field="angefragt">
                    {% if sponsor.angefragt == 1 %}Ja{% elif sponsor.angefragt == 0 %}Nein{% else %}{{ sponsor.angefragt }}{% endif %}
                </td>
                <td data-field="rueckmeldung">
                    {% if sponsor.rueckmeldung == 1 %}Ja{% elif sponsor.rueckmeldung == 0 %}Nein{% else %}{{ sponsor.rueckmeldung }}{% endif %}
                </td>
                <td data-field="sponsor_ja_nein">
                    {% if sponsor.sponsor_ja_nein == 1 %}Ja{% elif sponsor.sponsor_ja_nein == 0 %}Nein{% else %}{{ sponsor.sponsor_ja_nein }}{% endif %}
                </td>
                <td data-field="info">{{ sponsor.info }}</td>
                <td data-field="gegenleistung">{{ sponsor.gegenleistung }}</td>
                <td data-field="was">{{ sponsor.was }}</td>
                <td data-field="sponsoring_2024">{{ sponsor.sponsoring_2024 }}</td>
                <td>
                    {% if not sponsor.validiert and current_user and current_user['rolle'] == 'OB-Person' %}
                        <form method="post" action="{{ url_for('sponsoren.validate_sponsor', sponsor_id=sponsor.id) }}{% if search %}?search={{ search }}{% endif %}{% if f_angefragt %}&f_angefragt={{ f_angefragt }}{% endif %}{% if f_rueckmeldung %}&f_rueckmeldung={{ f_rueckmeldung }}{% endif %}{% if f_sponsor_ja_nein %}&f_sponsor_ja_nein={{ f_sponsor_ja_nein }}{% endif %}">
                            <button type="submit">Validieren</button>
                        </form>
                    {% elif sponsor.validiert %}
                        ✅
                    {% else %}
                        ❌
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <!-- Pagination und Per-Page Auswahl unten (wie oben!) -->
    <div class="pagination">
        <form method="get" class="per-page-form" style="display:inline;">
            <label for="per_page_bottom">Zeilen pro Seite:</label>
            <select name="per_page" id="per_page_bottom" onchange="this.form.submit()">
                {% for val in per_page_choices %}
                    <option value="{{val}}" {% if val == per_page %}selected{% endif %}>{{val}}</option>
                {% endfor %}
            </select>
            <input type="hidden" name="page" value="1">
            {% if search %}<input type="hidden" name="search" value="{{ search }}">{% endif %}
            {% if f_angefragt %}<input type="hidden" name="f_angefragt" value="{{ f_angefragt }}">{% endif %}
            {% if f_rueckmeldung %}<input type="hidden" name="f_rueckmeldung" value="{{ f_rueckmeldung }}">{% endif %}
            {% if f_sponsor_ja_nein %}<input type="hidden" name="f_sponsor_ja_nein" value="{{ f_sponsor_ja_nein }}">{% endif %}
            {% if f_validiert %}<input type="hidden" name="f_validiert" value="{{ f_validiert }}">{% endif %}
        </form>
        {% for p in range(1, total_pages+1) %}
            {% if p == page %}
                <span class="current">{{p}}</span>
            {% else %}
                <a href="?page={{p}}&per_page={{per_page}}{% if search %}&search={{ search }}{% endif %}{% if f_angefragt %}&f_angefragt={{ f_angefragt }}{% endif %}{% if f_rueckmeldung %}&f_rueckmeldung={{ f_rueckmeldung }}{% endif %}{% if f_sponsor_ja_nein %}&f_sponsor_ja_nein={{ f_sponsor_ja_nein }}{% endif %}{% if f_validiert %}&f_validiert={{ f_validiert }}{% endif %}">{{p}}</a>
            {% endif %}
        {% endfor %}
    </div>
</body>
</html>
"""

def bool_and_info(val):
    if val is None:
        return 0, ""
    s = str(val).strip().lower()
    if s in ["ja", "yes", "y", "1", "true"]:
        return 1, ""
    if s in ["nein", "no", "n", "0", "false"]:
        return 0, ""
    if s.startswith("ja"):
        return 1, val
    if s.startswith("nein"):
        return 0, val
    return 0, val

@sponsoren_bp.route('/', methods=['GET', 'POST'])
def index():
    current_user = get_current_user()
    if request.method == 'POST':
        name = request.form['name']
        adresse = request.form.get('adresse', '')
        emails = [e.strip() for e in request.form['emails'].split(',') if e.strip()]
        wichtig = request.form.get('wichtig', '')

        angefragt_bool, angefragt_info = bool_and_info(request.form.get('angefragt', ''))
        rueckmeldung_bool, rueckmeldung_info = bool_and_info(request.form.get('rueckmeldung', ''))
        sponsor_bool, sponsor_info = bool_and_info(request.form.get('sponsor_ja_nein', ''))

        gegenleistung = request.form.get('gegenleistung', '')
        was = request.form.get('was', '')
        sponsoring_2024 = request.form.get('sponsoring_2024', '')

        info_parts = []
        if angefragt_info:
            info_parts.append(f"Angefragt: {angefragt_info}")
        if sponsor_info:
            info_parts.append(f"Sponsor Ja/Nein: {sponsor_info}")
        if rueckmeldung_info:
            info_parts.append(f"Rückmeldung: {rueckmeldung_info}")
        info = " | ".join(info_parts)

        validiert = 0  # Neue Sponsoren sind nicht validiert

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sponsor (
                name, adresse, wichtig, angefragt, rueckmeldung, sponsor_ja_nein,
                info, gegenleistung, was, sponsoring_2024, validiert
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name, adresse, wichtig, angefragt_bool, rueckmeldung_bool, sponsor_bool,
            info, gegenleistung, was, sponsoring_2024, validiert
        ))
        sponsor_id = cursor.lastrowid
        for mail in emails:
            cursor.execute("INSERT INTO mailadresse (sponsor_id, mail) VALUES (?, ?)", (sponsor_id, mail))
        conn.commit()
        conn.close()
        return redirect(url_for('sponsoren.index'))

    # --- Filter auslesen ---
    search = request.args.get('search', '').strip()
    f_angefragt = request.args.get('f_angefragt', '')
    f_rueckmeldung = request.args.get('f_rueckmeldung', '')
    f_sponsor_ja_nein = request.args.get('f_sponsor_ja_nein', '')
    f_validiert = request.args.get('f_validiert', '')
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1
    try:
        per_page = int(request.args.get('per_page', 25))
    except ValueError:
        per_page = 25
    if per_page not in PER_PAGE_CHOICES:
        per_page = 25

    # Query dynamisch bauen
    where = []
    params = []
    if search:
        where.append("name LIKE ?")
        params.append(f"%{search}%")
    if f_angefragt in ('0', '1'):
        where.append("angefragt = ?")
        params.append(int(f_angefragt))
    if f_rueckmeldung in ('0', '1'):
        where.append("rueckmeldung = ?")
        params.append(int(f_rueckmeldung))
    if f_sponsor_ja_nein in ('0', '1'):
        where.append("sponsor_ja_nein = ?")
        params.append(int(f_sponsor_ja_nein))
    if f_validiert in ('0', '1'):
        where.append("validiert = ?")
        params.append(int(f_validiert))

    where_sql = "WHERE " + " AND ".join(where) if where else ""
    count_sql = f"SELECT COUNT(*) FROM sponsor {where_sql}"
    select_sql = f"SELECT * FROM sponsor {where_sql} ORDER BY id LIMIT ? OFFSET ?"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(count_sql, params)
    total_count = cursor.fetchone()[0]
    total_pages = max(1, math.ceil(total_count / per_page))
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages
    offset = (page - 1) * per_page

    params_with_limit = params + [per_page, offset]
    rows = cursor.execute(select_sql, params_with_limit).fetchall()

    sponsoren = []
    for sponsor_row in rows:
        sponsor = dict(sponsor_row)
        emails = [row['mail'] for row in cursor.execute("SELECT mail FROM mailadresse WHERE sponsor_id = ?", (sponsor['id'],))]
        sponsor['emails'] = emails
        sponsoren.append(sponsor)
    conn.close()

    return render_template_string(
        HTML,
        sponsoren=sponsoren,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        per_page_choices=PER_PAGE_CHOICES,
        search=search,
        f_angefragt=f_angefragt,
        f_rueckmeldung=f_rueckmeldung,
        f_sponsor_ja_nein=f_sponsor_ja_nein,
        f_validiert=f_validiert,
        current_user=current_user
    )

@sponsoren_bp.route('/validate/<int:sponsor_id>', methods=['POST'])
def validate_sponsor(sponsor_id):
    user = get_current_user()
    if not user or user['rolle'] != 'OB-Person':
        return "Nicht erlaubt", 403
    conn = get_db_connection()
    conn.execute("UPDATE sponsor SET validiert=1 WHERE id=?", (sponsor_id,))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for('sponsoren.index'))

@sponsoren_bp.route('/edit', methods=['POST'])
def edit_cell():
    data = request.get_json()
    sponsor_id = data.get('id')
    field = data.get('field')
    value = data.get('value')

    allowed_fields = {'name', 'adresse', 'wichtig', 'angefragt', 'rueckmeldung', 'sponsor_ja_nein', 'info', 'gegenleistung', 'was', 'sponsoring_2024'}
    if field not in allowed_fields:
        return jsonify({'error': 'Ungültiges Feld'}), 400

    if field in {'angefragt', 'rueckmeldung', 'sponsor_ja_nein'}:
        if str(value).lower() in ['1', 'ja', 'yes', 'true', 'y']:
            value = 1
        else:
            value = 0

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"UPDATE sponsor SET {field} = ? WHERE id = ?", (value, sponsor_id))
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500
    conn.close()
    return jsonify({'success': True})