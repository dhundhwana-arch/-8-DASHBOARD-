export type LocaleCode = "en" | "gu";

export interface AuthDictionary {
  // Brand & Shell
  brandTitle: string;
  moduleSubtitle: string;
  workshopLocationTag: string;
  openMenuLabel: string;
  closeMenuLabel: string;
  navSectionHeading: string;
  navDashboardOverview: string;
  navAdminAccounts: string;
  navActivityLogs: string;
  navActiveSession: string;

  // Auth & Session
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

  // Roles
  roleOwner: string;
  roleAdministrator: string;
  roleAuthorizedStaff: string;

  // Dashboard Header & Controls
  dashboardHeading: string;
  dashboardFullSubtitle: string;
  dashboardLimitedSubtitle: string;
  refreshButton: string;
  refreshingButton: string;
  loadingDashboard: string;
  dashboardLoadErrorHeading: string;
  retryButton: string;
  lastUpdatedLabel: string;
  integrationModeLive: string;
  integrationModeMock: string;

  // Mock / Dev Warning Banner
  mockBannerTitle: string;
  mockBannerBody: string;

  // 5-State Data Provenance Badges
  statusVerified: string;
  statusMockDev: string;
  statusContractUnconfigured: string;
  statusUnavailable: string;
  statusContractMismatch: string;
  metricNotAvailableNote: string;
  metricRoleRestrictedNote: string;

  // Summary Cards
  summarySectionHeading: string;
  cardTotalOrders: string;
  cardActiveProductionOrders: string;
  cardActiveWorkshopOrders: string;
  cardInStitchingOrders: string;
  cardReadyForDeliveryOrders: string;
  cardActiveCatalogueFabrics: string;
  cardAvailableVariants: string;
  cardActiveAdminAccounts: string;

  // Order Status Overview (Module 07)
  orderSectionHeading: string;
  orderSectionSubtitle: string;
  orderUnavailableTitle: string;
  stagePendingReview: string;
  stageAwaitingConfirmation: string;
  stageActiveOrders: string;
  stageCutting: string;
  stageStitching: string;
  stageFinishing: string;
  stageQualityCheck: string;
  stageReadyForDelivery: string;
  stageOnHold: string;
  stageUrgentActive: string;
  stageCompleted: string;
  stageCancelled: string;

  // Fabric Catalogue Overview (Module 02)
  fabricSectionHeading: string;
  fabricSectionSubtitle: string;
  fabricUnavailableTitle: string;
  fabricTotalActive: string;
  fabricActiveCategories: string;
  fabricDistinctColours: string;
  fabricTotalVariants: string;
  fabricAvailableVariants: string;
  fabricLowStockVariants: string;
  fabricOutOfStockVariants: string;
  fabricOnRequestVariants: string;
  fabricDiscontinuedVariants: string;

  // Pending Administrative Actions
  pendingActionsHeading: string;
  pendingActionsSubtitle: string;
  pendingActionsEmpty: string;
  pendingOrdersReview: string;
  pendingCustomerConfirmation: string;
  pendingQualityChecks: string;
  pendingReadyForDelivery: string;
  pendingFabricAttention: string;
  pendingSecurityReview: string;
  pendingWorkshopSettings: string;
  openSectionLink: string;

  // Operational Alerts
  alertsHeading: string;
  alertsSubtitle: string;
  alertsEmpty: string;

  // Integration Health Indicators
  integrationsHeading: string;
  integrationsSubtitle: string;
  latencyLabel: string;

  // Governance & Recent Activity (FULL scope)
  governanceHeading: string;
  governanceActiveUsers: string;
  governanceActiveSessions: string;
  governanceSecurityEvents24h: string;
  recentActivityHeading: string;
  recentActivityEmpty: string;

  // Secondary Implemented Pages (/users, /activity-logs, /session)
  usersPageHeading: string;
  usersPageSubtitle: string;
  usersColName: string;
  usersColUsername: string;
  usersColRole: string;
  usersColStatus: string;
  statusActive: string;
  statusDisabled: string;
  auditPageHeading: string;
  auditPageSubtitle: string;
  auditColTime: string;
  auditColActor: string;
  auditColAction: string;
  auditColResource: string;
  auditColOutcome: string;
  sessionsListHeading: string;
  currentSessionTag: string;
}

export const enAuthDictionary: AuthDictionary = {
  brandTitle: "CUSTOM SHIRT STUDIO",
  moduleSubtitle: "Small Business Admin Dashboard (Module 08)",
  workshopLocationTag: "Workshop Admin • Gujarat",
  openMenuLabel: "Open navigation menu",
  closeMenuLabel: "Close navigation menu",
  navSectionHeading: "Authorized Sections",
  navDashboardOverview: "Dashboard Overview",
  navAdminAccounts: "Admin Accounts",
  navActivityLogs: "Activity & Audit Logs",
  navActiveSession: "Active Session",

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
    "Authenticated session cookie protection, CSRF token binding, and backend RBAC enforcement are active.",
  roleLabel: "Assigned Role",
  authModeLabel: "Authentication Mode",
  sessionIdLabel: "Active Session ID",
  accessDeniedHeading: "Access Restricted",
  accessDeniedMessage: "Your assigned role does not have permission to view this section.",
  languageSwitchLabel: "ભાષા: ગુજરાતી",
  loadingSession: "Verifying session...",

  roleOwner: "Owner",
  roleAdministrator: "Administrator",
  roleAuthorizedStaff: "Authorized Staff",

  dashboardHeading: "Workshop Dashboard Overview",
  dashboardFullSubtitle:
    "Verified operational status across Module 08 governance and connected Custom Shirt Studio services.",
  dashboardLimitedSubtitle:
    "Assigned workshop stage status and fabric availability for authorized tailoring staff.",
  refreshButton: "Refresh",
  refreshingButton: "Refreshing...",
  loadingDashboard: "Loading verified dashboard status...",
  dashboardLoadErrorHeading: "Unable to load dashboard overview",
  retryButton: "Retry",
  lastUpdatedLabel: "Checked",
  integrationModeLive: "Live Contract Mode",
  integrationModeMock: "MOCK_DEV Mode",

  mockBannerTitle: "Development Mock Data Active (MOCK_DEV)",
  mockBannerBody:
    "Simulated fixture counts are shown for local development/testing only. Do NOT treat MOCK_DEV numbers as live workshop orders or catalogue inventory.",

  statusVerified: "Verified Live",
  statusMockDev: "Mock / Dev Data",
  statusContractUnconfigured: "Contract Unconfigured",
  statusUnavailable: "Service Unavailable",
  statusContractMismatch: "Contract Mismatch",
  metricNotAvailableNote: "Unavailable — never shown as zero",
  metricRoleRestrictedNote: "Restricted for current role",

  summarySectionHeading: "Key Operational Summary",
  cardTotalOrders: "Total Recorded Orders",
  cardActiveProductionOrders: "Orders In Production",
  cardActiveWorkshopOrders: "Active Workshop Orders",
  cardInStitchingOrders: "Orders In Stitching",
  cardReadyForDeliveryOrders: "Ready for Delivery",
  cardActiveCatalogueFabrics: "Active Catalogue Fabrics",
  cardAvailableVariants: "Available Fabric Variants",
  cardActiveAdminAccounts: "Active Admin Accounts",

  orderSectionHeading: "Order & Tailoring Stage Overview (Module 07)",
  orderSectionSubtitle:
    "Displays tailoring workflow counts strictly when Module 07 exposes a verified contract.",
  orderUnavailableTitle: "Order Metrics Unavailable",
  stagePendingReview: "Pending Review",
  stageAwaitingConfirmation: "Awaiting Confirmation",
  stageActiveOrders: "Active Orders",
  stageCutting: "In Cutting",
  stageStitching: "In Stitching",
  stageFinishing: "In Finishing",
  stageQualityCheck: "Quality Check",
  stageReadyForDelivery: "Ready for Delivery",
  stageOnHold: "On Hold",
  stageUrgentActive: "Urgent Active",
  stageCompleted: "Completed",
  stageCancelled: "Cancelled",

  fabricSectionHeading: "Fabric Catalogue Overview (Module 02)",
  fabricSectionSubtitle:
    "Read-only catalogue & variant availability summary via Module 02 public /api/v1 contract.",
  fabricUnavailableTitle: "Fabric Catalogue Metrics Unavailable",
  fabricTotalActive: "Active Fabrics",
  fabricActiveCategories: "Active Categories",
  fabricDistinctColours: "Distinct Colours",
  fabricTotalVariants: "Total Variants",
  fabricAvailableVariants: "Available",
  fabricLowStockVariants: "Low Stock",
  fabricOutOfStockVariants: "Out of Stock",
  fabricOnRequestVariants: "On Request",
  fabricDiscontinuedVariants: "Discontinued",

  pendingActionsHeading: "Pending Administrative Actions",
  pendingActionsSubtitle: "Shown only where verified upstream or local governance records exist.",
  pendingActionsEmpty: "No verified pending administrative actions at this time.",
  pendingOrdersReview: "Orders awaiting initial review",
  pendingCustomerConfirmation: "Orders awaiting customer confirmation",
  pendingQualityChecks: "Garments awaiting quality check",
  pendingReadyForDelivery: "Completed garments ready for handover",
  pendingFabricAttention: "Fabric variants marked low stock or out of stock",
  pendingSecurityReview: "Failed or denied security events in last 24h",
  pendingWorkshopSettings: "Owner-approved workshop settings not yet recorded",
  openSectionLink: "Open",

  alertsHeading: "Operational & Integration Alerts",
  alertsSubtitle: "Upstream connectivity, contract verification, and security notices.",
  alertsEmpty: "No active operational or integration warnings.",

  integrationsHeading: "Ecosystem Integration Health",
  integrationsSubtitle: "Live provenance status across Custom Shirt Studio modules.",
  latencyLabel: "Latency",

  governanceHeading: "Module 08 Local Governance Summary",
  governanceActiveUsers: "Active Admin Users",
  governanceActiveSessions: "Active Sessions",
  governanceSecurityEvents24h: "Security Alerts (24h)",
  recentActivityHeading: "Recent Administrative Activity",
  recentActivityEmpty: "No administrative activity recorded yet.",

  usersPageHeading: "Administrator & Staff Accounts",
  usersPageSubtitle: "Verified local Module 08 accounts governed by role-based access control.",
  usersColName: "Display Name",
  usersColUsername: "Username",
  usersColRole: "Role",
  usersColStatus: "Status",
  statusActive: "Active",
  statusDisabled: "Disabled",
  auditPageHeading: "Administrative Activity & Audit Logs",
  auditPageSubtitle: "Immutable append-only operational and security event trail.",
  auditColTime: "Timestamp (UTC)",
  auditColActor: "Actor",
  auditColAction: "Action",
  auditColResource: "Resource",
  auditColOutcome: "Outcome",
  sessionsListHeading: "Your Active Sessions",
  currentSessionTag: "Current",
};

export const guAuthDictionary: AuthDictionary = {
  brandTitle: "કસ્ટમ શર્ટ સ્ટુડિયો",
  moduleSubtitle: "નાના વ્યવસાય એડમિન ડેશબોર્ડ (મોડ્યુલ ૦૮)",
  workshopLocationTag: "વર્કશોપ એડમિન • ગુજરાત",
  openMenuLabel: "નેવિગેશન મેનૂ ખોલો",
  closeMenuLabel: "નેવિગેશન મેનૂ બંધ કરો",
  navSectionHeading: "અધિકૃત વિભાગો",
  navDashboardOverview: "ડેશબોર્ડ ઝાંખી",
  navAdminAccounts: "એડમિન ખાતાઓ",
  navActivityLogs: "પ્રવૃત્તિ અને ઓડિટ લોગ",
  navActiveSession: "સક્રિય સત્ર",

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
    "સુરક્ષિત સત્ર કૂકી, CSRF સુરક્ષા અને બેકએન્ડ RBAC નિયંત્રણ સક્રિય છે.",
  roleLabel: "સોંપેલ ભૂમિકા",
  authModeLabel: "પ્રમાણીકરણ સ્થિતિ",
  sessionIdLabel: "સક્રિય સત્ર ઓળખ",
  accessDeniedHeading: "પ્રવેશ મર્યાદિત",
  accessDeniedMessage: "તમારી ભૂમિકાને આ વિભાગ જોવાની પરવાનગી નથી.",
  languageSwitchLabel: "Language: English",
  loadingSession: "સત્ર ચકાસાઈ રહ્યું છે...",

  roleOwner: "માલિક (Owner)",
  roleAdministrator: "એડમિનિસ્ટ્રેટર",
  roleAuthorizedStaff: "અધિકૃત સ્ટાફ",

  dashboardHeading: "વર્કશોપ ડેશબોર્ડ ઝાંખી",
  dashboardFullSubtitle:
    "મોડ્યુલ ૦૮ વહીવટ અને જોડાયેલ કસ્ટમ શર્ટ સ્ટુડિયો સેવાઓની ચકાસાયેલ સ્થિતિ.",
  dashboardLimitedSubtitle:
    "અધિકૃત ટેલરિંગ સ્ટાફ માટે વર્કશોપ કામગીરી અને કાપડ ઉપલબ્ધતાની સ્થિતિ.",
  refreshButton: "તાજું કરો",
  refreshingButton: "લોડ થઈ રહ્યું છે...",
  loadingDashboard: "ડેશબોર્ડની ચકાસાયેલ માહિતી લોડ થઈ રહી છે...",
  dashboardLoadErrorHeading: "ડેશબોર્ડ માહિતી લોડ કરી શકાઈ નથી",
  retryButton: "ફરી પ્રયાસ કરો",
  lastUpdatedLabel: "ચકાસણી સમય",
  integrationModeLive: "લાઇવ કોન્ટ્રાક્ટ મોડ",
  integrationModeMock: "MOCK_DEV મોડ",

  mockBannerTitle: "ડેવલપમેન્ટ મોક ડેટા સક્રિય છે (MOCK_DEV)",
  mockBannerBody:
    "આ આંકડા ફક્ત સ્થાનિક પરીક્ષણ માટેના નમૂના છે. તેને વાસ્તવિક વર્કશોપ ઓર્ડર અથવા કાપડના સ્ટોક તરીકે ગણશો નહીં.",

  statusVerified: "ચકાસાયેલ લાઇવ",
  statusMockDev: "મોક / ટેસ્ટ ડેટા",
  statusContractUnconfigured: "કોન્ટ્રાક્ટ અપ્રાપ્ય",
  statusUnavailable: "સેવા અનુપલબ્ધ",
  statusContractMismatch: "કોન્ટ્રાક્ટ વિસંગતતા",
  metricNotAvailableNote: "માહિતી અનુપલબ્ધ — શૂન્ય તરીકે દર્શાવેલ નથી",
  metricRoleRestrictedNote: "આ ભૂમિકા માટે મર્યાદિત",

  summarySectionHeading: "મુખ્ય કામગીરી સારાંશ",
  cardTotalOrders: "કુલ નોંધાયેલ ઓર્ડર",
  cardActiveProductionOrders: "સિલાઈ/ઉત્પાદનમાં ઓર્ડર",
  cardActiveWorkshopOrders: "સક્રિય વર્કશોપ ઓર્ડર",
  cardInStitchingOrders: "સિલાઈ (Stitching) માં ઓર્ડર",
  cardReadyForDeliveryOrders: "ડિલિવરી માટે તૈયાર",
  cardActiveCatalogueFabrics: "સક્રિય કેટલોગ કાપડ",
  cardAvailableVariants: "ઉપલબ્ધ કાપડ રંગ/પ્રકાર",
  cardActiveAdminAccounts: "સક્રિય એડમિન ખાતાઓ",

  orderSectionHeading: "ઓર્ડર અને ટેલરિંગ તબક્કાની ઝાંખી (મોડ્યુલ ૦૭)",
  orderSectionSubtitle:
    "જ્યારે મોડ્યુલ ૦૭ નો ચકાસાયેલ કોન્ટ્રાક્ટ ઉપલબ્ધ હોય ત્યારે જ ઓર્ડરની સંખ્યા દર્શાવાય છે.",
  orderUnavailableTitle: "ઓર્ડરની માહિતી હાલમાં અનુપલબ્ધ છે",
  stagePendingReview: "સમીક્ષા બાકી",
  stageAwaitingConfirmation: "ગ્રાહક મંજૂરી બાકી",
  stageActiveOrders: "સક્રિય ઓર્ડર",
  stageCutting: "કટિંગમાં",
  stageStitching: "સિલાઈમાં",
  stageFinishing: "ફિનિશિંગમાં",
  stageQualityCheck: "ગુણવત્તા ચકાસણી",
  stageReadyForDelivery: "ડિલિવરી માટે તૈયાર",
  stageOnHold: "હોલ્ડ પર",
  stageUrgentActive: "તાત્કાલિક (Urgent)",
  stageCompleted: "પૂર્ણ થયેલ",
  stageCancelled: "રદ થયેલ",

  fabricSectionHeading: "કાપડ કેટલોગ ઝાંખી (મોડ્યુલ ૦૨)",
  fabricSectionSubtitle:
    "મોડ્યુલ ૦૨ ના ચકાસાયેલ જાહેર /api/v1 કોન્ટ્રાક્ટ પરથી કાપડની ઉપલબ્ધતા.",
  fabricUnavailableTitle: "કાપડ કેટલોગ માહિતી અનુપલબ્ધ છે",
  fabricTotalActive: "સક્રિય કાપડ",
  fabricActiveCategories: "સક્રિય શ્રેણીઓ",
  fabricDistinctColours: "ઉપલબ્ધ રંગો",
  fabricTotalVariants: "કુલ વેરિઅન્ટ્સ",
  fabricAvailableVariants: "ઉપલબ્ધ",
  fabricLowStockVariants: "ઓછો જથ્થો",
  fabricOutOfStockVariants: "સ્ટોક બહાર",
  fabricOnRequestVariants: "માંગ પર ઉપલબ્ધ",
  fabricDiscontinuedVariants: "બંધ કરેલ",

  pendingActionsHeading: "બાકી વહીવટી કાર્યો",
  pendingActionsSubtitle: "ફક્ત ચકાસાયેલ માહિતી ઉપલબ્ધ હોય તેવા જ કાર્યો અહીં દર્શાવાય છે.",
  pendingActionsEmpty: "હાલમાં કોઈ ચકાસાયેલ બાકી વહીવટી કાર્ય નથી.",
  pendingOrdersReview: "પ્રાથમિક સમીક્ષા માટે બાકી ઓર્ડર",
  pendingCustomerConfirmation: "ગ્રાહકની પુષ્ટિ માટે બાકી ઓર્ડર",
  pendingQualityChecks: "ગુણવત્તા ચકાસણી માટે બાકી કપડાં",
  pendingReadyForDelivery: "ડિલિવરી માટે તૈયાર કપડાં",
  pendingFabricAttention: "ઓછા સ્ટોક અથવા સ્ટોક બહારના કાપડ વેરિઅન્ટ્સ",
  pendingSecurityReview: "છેલ્લા ૨૪ કલાકમાં નિષ્ફળ અથવા નકારાયેલ સુરક્ષા ઘટનાઓ",
  pendingWorkshopSettings: "માલિક-મંજૂર વર્કશોપ સેટિંગ્સ હજુ નોંધાયેલ નથી",
  openSectionLink: "જુઓ",

  alertsHeading: "કામગીરી અને સિસ્ટમ સૂચનાઓ",
  alertsSubtitle: "જોડાયેલ મોડ્યુલની સ્થિતિ, કોન્ટ્રાક્ટ ચકાસણી અને સુરક્ષા ચેતવણીઓ.",
  alertsEmpty: "હાલમાં કોઈ સક્રિય કામગીરી અથવા સિસ્ટમ ચેતવણી નથી.",

  integrationsHeading: "સિસ્ટમ જોડાણ (Integration) સ્વાસ્થ્ય",
  integrationsSubtitle: "કસ્ટમ શર્ટ સ્ટુડિયોના તમામ મોડ્યુલની લાઇવ સ્થિતિ.",
  latencyLabel: "પ્રતિસાદ સમય",

  governanceHeading: "મોડ્યુલ ૦૮ સ્થાનિક વહીવટી સારાંશ",
  governanceActiveUsers: "સક્રિય એડમિન વપરાશકર્તાઓ",
  governanceActiveSessions: "સક્રિય સત્રો",
  governanceSecurityEvents24h: "સુરક્ષા ચેતવણીઓ (૨૪ કલાક)",
  recentActivityHeading: "તાજેતરની વહીવટી પ્રવૃત્તિ",
  recentActivityEmpty: "હજુ સુધી કોઈ વહીવટી પ્રવૃત્તિ નોંધાઈ નથી.",

  usersPageHeading: "એડમિનિસ્ટ્રેટર અને સ્ટાફ ખાતાઓ",
  usersPageSubtitle: "ભૂમિકા-આધારિત નિયંત્રણ હેઠળના સ્થાનિક મોડ્યુલ ૦૮ ખાતાઓ.",
  usersColName: "નામ",
  usersColUsername: "વપરાશકર્તા નામ",
  usersColRole: "ભૂમિકા",
  usersColStatus: "સ્થિતિ",
  statusActive: "સક્રિય",
  statusDisabled: "નિષ્ક્રિય",
  auditPageHeading: "વહીવટી પ્રવૃત્તિ અને ઓડિટ લોગ",
  auditPageSubtitle: "ફેરફાર ન કરી શકાય તેવો સુરક્ષિત ઓડિટ રેકોર્ડ.",
  auditColTime: "સમય (UTC)",
  auditColActor: "વપરાશકર્તા",
  auditColAction: "ક્રિયા",
  auditColResource: "સંસાધન",
  auditColOutcome: "પરિણામ",
  sessionsListHeading: "તમારા સક્રિય સત્રો",
  currentSessionTag: "વર્તમાન",
};
