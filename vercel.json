/**
 * i18n.js – Lightweight internationalization (DE default, EN optional)
 * No build step, no dependencies.
 * Usage in HTML: <span data-i18n="key"></span>
 * Usage in JS:   t('key')  or  t('key', { var: 'value' })
 */

const LANG_KEY = 'ga-lang';

const TRANSLATIONS = {
  de: {
    // Auth
    app_tagline:       'Dein persönlicher Espresso-Assistent',
    login:             'Anmelden',
    register:          'Registrieren',
    email:             'E-Mail',
    password:          'Passwort',
    no_account:        'Noch kein Konto?',
    has_account:       'Bereits registriert?',
    logout:            'Abmelden',
    password_hint:     'Mindestens 8 Zeichen',

    // Nav
    tab_shots:         'Shots',
    tab_beans:         'Bohnen',
    tab_recommend:     'Empfehlung',
    tab_import:        'Import',

    // Shots
    shots_title:       'Meine Shots',
    new_shot:          'Neuer Shot',
    grind_size:        'Mahlgrad',
    grind_hint:        'Deine mühlenspezifische Skala (z. B. 1–40)',
    extraction_time:   'Extraktionszeit',
    extraction_hint:   'Sekunden (Ziel: 25–30s)',
    brew_weight:       'Auslaufgewicht (g)',
    dose:              'Einwaage (g)',
    brew_ratio:        'Brew Ratio',
    rating:            'Bewertung',
    notes:             'Notizen',
    notes_placeholder: 'Aroma, Textur, Nachgeschmack…',
    save_shot:         'Shot speichern',
    no_shots:          'Noch keine Shots. Leg los!',
    shots_saved:       '{{n}} Shots gespeichert',
    delete_confirm:    'Shot wirklich löschen?',
    bean_label:        'Bohne',
    select_bean:       '— Bohne wählen —',
    no_bean:           'Keine Bohne zugeordnet',

    // Timer
    timer_start:       'Start',
    timer_stop:        'Stopp',
    timer_reset:       'Reset',
    timer_hint:        'Timer direkt in Feld übernehmen',

    // Beans
    beans_title:       'Meine Bohnen',
    new_bean:          'Neue Bohne',
    bean_name:         'Name / Bezeichnung',
    roast_label:       'Röstgrad',
    roast_light:       'Hell',
    roast_medium:      'Mittel',
    roast_dark:        'Dunkel',
    origin:            'Herkunft (optional)',
    save_bean:         'Bohne speichern',
    no_beans:          'Noch keine Bohnen eingetragen.',
    shots_count:       '{{n}} Shot(s)',

    // Recommendation
    recommend_title:   'ML-Empfehlung',
    target_time:       'Zielzeit (s)',
    target_time_hint:  'Gewünschte Extraktionszeit, z. B. 27',
    brew_weight_in:    'Auslaufgewicht (g)',
    dose_in:           'Einwaage (g)',
    get_recommend:     'Empfehlung berechnen',
    optimal_grind:     'Empfohlener Mahlgrad',
    predicted_time:    'Vorhergesagte Zeit',
    confidence:        'Konfidenz',
    confidence_high:   'Hoch',
    confidence_medium: 'Mittel',
    confidence_low:    'Niedrig',
    model_info:        '{{n}} Shots · R² {{r2}}',
    no_model:          'Zu wenig Daten',
    need_more_shots:   'Mindestens {{n}} Shots mit verschiedenen Mahlgraden nötig.',
    direction_finer:   '→ Feiner mahlen, um die Zeit zu verkürzen',
    direction_coarser: '→ Gröber mahlen, um die Zeit zu verlängern',

    // Import
    import_title:      'JSON-Import',
    import_desc:       'Importiere Shots aus Decent Espresso oder deinem eigenen Format.',
    import_format:     'Format: <code>{"shots":[{"grind_size":20,"extraction_time":27,"brew_weight":36}]}</code>',
    import_btn:        'Datei wählen & importieren',
    import_success:    '{{n}} Shot(s) importiert',
    import_skipped:    '{{n}} übersprungen',
    import_drop:       'JSON-Datei hier ablegen oder klicken',

    // General
    loading:           'Laden…',
    error:             'Fehler',
    success:           'Gespeichert',
    delete:            'Löschen',
    cancel:            'Abbrechen',
    save:              'Speichern',
    seconds_abbr:      's',
    grams_abbr:        'g',
  },

  en: {
    app_tagline:       'Your personal espresso assistant',
    login:             'Login',
    register:          'Register',
    email:             'Email',
    password:          'Password',
    no_account:        'No account yet?',
    has_account:       'Already registered?',
    logout:            'Log out',
    password_hint:     'At least 8 characters',

    tab_shots:         'Shots',
    tab_beans:         'Beans',
    tab_recommend:     'Advisor',
    tab_import:        'Import',

    shots_title:       'My Shots',
    new_shot:          'New Shot',
    grind_size:        'Grind Size',
    grind_hint:        'Your mill-specific scale (e.g. 1–40)',
    extraction_time:   'Extraction Time',
    extraction_hint:   'Seconds (target: 25–30s)',
    brew_weight:       'Brew Weight (g)',
    dose:              'Dose (g)',
    brew_ratio:        'Brew Ratio',
    rating:            'Rating',
    notes:             'Notes',
    notes_placeholder: 'Aroma, texture, aftertaste…',
    save_shot:         'Save Shot',
    no_shots:          'No shots yet. Start brewing!',
    shots_saved:       '{{n}} shots saved',
    delete_confirm:    'Delete this shot?',
    bean_label:        'Bean',
    select_bean:       '— Select bean —',
    no_bean:           'No bean assigned',

    timer_start:       'Start',
    timer_stop:        'Stop',
    timer_reset:       'Reset',
    timer_hint:        'Timer value auto-fills the field',

    beans_title:       'My Beans',
    new_bean:          'New Bean',
    bean_name:         'Name / Label',
    roast_label:       'Roast',
    roast_light:       'Light',
    roast_medium:      'Medium',
    roast_dark:        'Dark',
    origin:            'Origin (optional)',
    save_bean:         'Save Bean',
    no_beans:          'No beans added yet.',
    shots_count:       '{{n}} shot(s)',

    recommend_title:   'ML Advisor',
    target_time:       'Target Time (s)',
    target_time_hint:  'Desired extraction time, e.g. 27',
    brew_weight_in:    'Brew Weight (g)',
    dose_in:           'Dose (g)',
    get_recommend:     'Get Recommendation',
    optimal_grind:     'Recommended Grind',
    predicted_time:    'Predicted Time',
    confidence:        'Confidence',
    confidence_high:   'High',
    confidence_medium: 'Medium',
    confidence_low:    'Low',
    model_info:        '{{n}} shots · R² {{r2}}',
    no_model:          'Insufficient data',
    need_more_shots:   'Need at least {{n}} shots with different grind sizes.',
    direction_finer:   '→ Grind finer to shorten the time',
    direction_coarser: '→ Grind coarser to lengthen the time',

    import_title:      'JSON Import',
    import_desc:       'Import shots from Decent Espresso or your own format.',
    import_format:     'Format: <code>{"shots":[{"grind_size":20,"extraction_time":27,"brew_weight":36}]}</code>',
    import_btn:        'Choose file & import',
    import_success:    '{{n}} shot(s) imported',
    import_skipped:    '{{n}} skipped',
    import_drop:       'Drop JSON file here or click',

    loading:           'Loading…',
    error:             'Error',
    success:           'Saved',
    delete:            'Delete',
    cancel:            'Cancel',
    save:              'Save',
    seconds_abbr:      's',
    grams_abbr:        'g',
  },
};

// ── State ─────────────────────────────────────────────────────────────────────
let _lang = localStorage.getItem(LANG_KEY) || 'de';

// ── Core functions ────────────────────────────────────────────────────────────

/** Translate a key with optional variable interpolation */
function t(key, vars = {}) {
  const dict = TRANSLATIONS[_lang] || TRANSLATIONS.de;
  let str = dict[key] ?? TRANSLATIONS.de[key] ?? key;
  for (const [k, v] of Object.entries(vars)) {
    str = str.replaceAll(`{{${k}}}`, v);
  }
  return str;
}

/** Apply translations to all [data-i18n] elements in DOM */
function applyTranslations() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.dataset.i18n;
    // Use innerHTML for keys that contain HTML (import_format etc.)
    if (key === 'import_format') {
      el.innerHTML = t(key);
    } else {
      el.textContent = t(key);
    }
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  document.documentElement.lang = _lang;
}

function setLang(lang) {
  if (!TRANSLATIONS[lang]) return;
  _lang = lang;
  localStorage.setItem(LANG_KEY, lang);
  applyTranslations();
  // Dispatch event so other modules can react
  document.dispatchEvent(new CustomEvent('langchange', { detail: { lang } }));
}

function getLang() { return _lang; }

// Apply on load
document.addEventListener('DOMContentLoaded', applyTranslations);
