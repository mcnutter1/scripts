from flask import Flask, request, render_template, redirect, url_for, flash, Response
import ldap

app = Flask(__name__)
app.secret_key = 'your_secret_key'

LDAP_SERVER = 'ldap://10.10.100.20'
LDAP_BASE_DN = 'dc=corp,dc=inovagenix,dc=com'
LDAP_USER_DN = 'ou=People'
LDAP_GROUP_DN = 'ou=groups'
LDAP_USER_LOGIN_ATTRIBUTE = 'samAccountName'
LDAP_BIND_USER_DN = None
LDAP_BIND_USER_PASSWORD = None

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'password':

            return Response(
                'Login Successful!\n'
                'You have used default credentials', status=200,mimetype='text/plain'
            )
            

        if authenticate(username, password):
            flash('Login successful!', 'success')
            return redirect(url_for('index'))  # Redirect to another page or dashboard
        else:
            flash('Invalid credentials, please try again.', 'danger')
    return render_template('login.html')

def authenticate(username, password):
    import ldap
    conn = ldap.initialize(LDAP_SERVER)
    conn.set_option(ldap.OPT_REFERRALS, 0)
    try:
        conn.simple_bind_s(f'{LDAP_USER_LOGIN_ATTRIBUTE}={username},{LDAP_USER_DN},{LDAP_BASE_DN}', password)
        return True
    except ldap.INVALID_CREDENTIALS:
        return False
    finally:
        conn.unbind()
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
