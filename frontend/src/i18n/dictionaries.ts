export type LocaleCode = "en" | "gu";

export interface AuthDictionary {
  brandTitle: string;
  moduleSubtitle: string;
  loginHeading: string;
  loginSubheading: string;
  usernameLabel: string;
  passwordLabel: string;
  signInButton: string;
  signingInButton: string;
  signOutButton: string;
  invalidCredentialsError: string;
  rateLimitedError: string;
  genericError: string;
  sessionActiveHeading: string;
  sessionActiveNote: string;
  roleLabel: string;
  authModeLabel: string;
  sessionIdLabel: string;
  accessDeniedHeading: string;
  accessDeniedMessage: string;
  languageSwitchLabel: string;
  loadingSession: string;
}

export const enAuthDictionary: AuthDictionary = {
  brandTitle: "CUSTOM SHIRT STUDIO",
  moduleSubtitle: "Small Business Admin Access (Module 08)",
  loginHeading: "Administrator Sign In",
  loginSubheading: "Authorized workshop owner, administrator, and staff access only.",
  usernameLabel: "Username",
  passwordLabel: "Password",
  signInButton: "Sign In",
  signingInButton: "Signing in...",
  signOutButton: "Sign Out",
  invalidCredentialsError: "Invalid username or password.",
  rateLimitedError: "Too many login attempts. Please wait before trying again.",
  genericError: "Unable to complete request. Please try again.",
  sessionActiveHeading: "Authenticated Session Active",
  sessionActiveNote:
    "Phase 03 authentication, session cookie protection, CSRF token binding, and backend RBAC enforcement are active.",
  roleLabel: "Assigned Role",
  authModeLabel: "Authentication Mode",
  sessionIdLabel: "Active Session ID",
  accessDeniedHeading: "Access Restricted",
  accessDeniedMessage: "Your assigned role does not have permission to view this section.",
  languageSwitchLabel: "ભાષા: ગુજરાતી",
  loadingSession: "Verifying session...",
};

export const guAuthDictionary: AuthDictionary = {
  brandTitle: "કસ્ટમ શર્ટ સ્ટુડિયો",
  moduleSubtitle: "નાના વ્યવસાય એડમિન પ્રવેશ (મોડ્યુલ ૦૮)",
  loginHeading: "એડમિન સાઇન ઇન",
  loginSubheading: "ફક્ત અધિકૃત માલિક, એડમિનિસ્ટ્રેટર અને સ્ટાફ માટે પ્રવેશ.",
  usernameLabel: "વપરાશકર્તા નામ",
  passwordLabel: "પાસવર્ડ",
  signInButton: "સાઇન ઇન કરો",
  signingInButton: "સાઇન ઇન થઈ રહ્યું છે...",
  signOutButton: "સાઇન આઉટ",
  invalidCredentialsError: "અમાન્ય વપરાશકર્તા નામ અથવા પાસવર્ડ.",
  rateLimitedError: "ઘણા બધા લોગિન પ્રયાસો થયા છે. કૃપા કરીને થોડી વાર રાહ જુઓ.",
  genericError: "વિનંતી પૂર્ણ થઈ શકી નથી. ફરી પ્રયાસ કરો.",
  sessionActiveHeading: "પ્રમાણિત સત્ર સક્રિય છે",
  sessionActiveNote:
    "તબક્કો ૦૩ પ્રમાણીકરણ, સુરક્ષિત સત્ર કૂકી, CSRF સુરક્ષા અને બેકએન્ડ RBAC નિયંત્રણ સક્રિય છે.",
  roleLabel: "સોંપેલ ભૂમિકા",
  authModeLabel: "પ્રમાણીકરણ સ્થિતિ",
  sessionIdLabel: "સક્રિય સત્ર ઓળખ",
  accessDeniedHeading: "પ્રવેશ મર્યાદિત",
  accessDeniedMessage: "તમારી ભૂમિકાને આ વિભાગ જોવાની પરવાનગી નથી.",
  languageSwitchLabel: "Language: English",
  loadingSession: "સત્ર ચકાસાઈ રહ્યું છે...",
};
