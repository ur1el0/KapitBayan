import { lazy, Suspense } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { useAuth } from "./context/auth-context";
import { ProtectedRoute } from "./components/core/ProtectedRoute";
import { AdminLayout } from "./components/layout/AdminLayout";
import { CitizenLayout } from "./components/layout/CitizenLayout";
import { ErrorBoundary } from "./components/core/ErrorBoundary";
import { RouteLoadingFallback } from "./components/core/RouteLoadingFallback";

const Login = lazy(() =>
    import("./pages/auth/Login").then(({ Login }) => ({ default: Login })),
);
const Register = lazy(() =>
    import("./pages/auth/Register").then(({ Register }) => ({ default: Register })),
);
const OfficialRegistration = lazy(() =>
    import("./pages/auth/OfficialRegistration").then(({ OfficialRegistration }) => ({ default: OfficialRegistration })),
);
const Dashboard = lazy(() =>
    import("./pages/admin/Dashboard").then(({ Dashboard }) => ({ default: Dashboard })),
);
const CitizenDocuments = lazy(() =>
    import("./pages/citizen/CitizenDocuments").then(({ CitizenDocuments }) => ({ default: CitizenDocuments })),
);
const CitizenQueue = lazy(() =>
    import("./pages/citizen/CitizenQueue").then(({ CitizenQueue }) => ({ default: CitizenQueue })),
);
const CitizenBulletin = lazy(() =>
    import("./pages/citizen/CitizenBulletin").then(({ CitizenBulletin }) => ({ default: CitizenBulletin })),
);
const DocumentRequests = lazy(() =>
    import("./pages/services/DocumentRequests").then(({ DocumentRequests }) => ({ default: DocumentRequests })),
);
const IssueReports = lazy(() =>
    import("./pages/services/IssueReports").then(({ IssueReports }) => ({ default: IssueReports })),
);
const Communications = lazy(() =>
    import("./pages/services/Communications").then(({ Communications }) => ({ default: Communications })),
);
const LiveQueue = lazy(() =>
    import("./pages/services/LiveQueue").then(({ LiveQueue }) => ({ default: LiveQueue })),
);
const AdminProfile = lazy(() =>
    import("./pages/admin/AdminProfile").then(({ AdminProfile }) => ({ default: AdminProfile })),
);
const Settings = lazy(() =>
    import("./pages/admin/Settings").then(({ Settings }) => ({ default: Settings })),
);
const Notifications = lazy(() =>
    import("./pages/community/Notifications").then(({ Notifications }) => ({ default: Notifications })),
);
const Faqs = lazy(() =>
    import("./pages/community/Faqs").then(({ Faqs }) => ({ default: Faqs })),
);
const DILGDashboard = lazy(() =>
    import("./pages/admin/DILGDashboard").then(({ DILGDashboard }) => ({ default: DILGDashboard })),
);
const DILGAccountSupport = lazy(() =>
    import("./pages/admin/DILGAccountSupport").then(({ DILGAccountSupport }) => ({ default: DILGAccountSupport })),
);
const BarangaySettings = lazy(() =>
    import("./pages/admin/BarangaySettings").then(({ BarangaySettings }) => ({ default: BarangaySettings })),
);
const BarangayApplications = lazy(() =>
    import("./pages/admin/BarangayApplications").then(({ BarangayApplications }) => ({ default: BarangayApplications })),
);
const ForgotPassword = lazy(() =>
    import("./pages/auth/ForgotPassword").then(({ ForgotPassword }) => ({ default: ForgotPassword })),
);
const ResetPassword = lazy(() =>
    import("./pages/auth/ResetPassword").then(({ ResetPassword }) => ({ default: ResetPassword })),
);
const ResidentsHub = lazy(() =>
    import("./pages/community/ResidentsHub").then(({ ResidentsHub }) => ({ default: ResidentsHub })),
);
const PublicQueueDisplay = lazy(() =>
    import("./pages/public/PublicQueueDisplay").then(({ PublicQueueDisplay }) => ({ default: PublicQueueDisplay })),
);
const PublicAnnouncements = lazy(() =>
    import("./pages/public/PublicAnnouncements").then(({ PublicAnnouncements }) => ({ default: PublicAnnouncements })),
);
const PublicNoticeRedirect = lazy(() =>
    import("./pages/public/PublicNoticeRedirect").then(({ PublicNoticeRedirect }) => ({ default: PublicNoticeRedirect })),
);
const AidRequests = lazy(() =>
    import("./pages/citizen/AidRequests").then(({ AidRequests }) => ({ default: AidRequests })),
);
const ResidentHelp = lazy(() =>
    import("./pages/citizen/ResidentHelp").then(({ ResidentHelp }) => ({ default: ResidentHelp })),
);
const ResidentTutorial = lazy(() =>
    import("./pages/citizen/ResidentTutorial").then(({ ResidentTutorial }) => ({ default: ResidentTutorial })),
);
const ResidentProfileSettings = lazy(() =>
    import("./pages/citizen/ResidentProfileSettings").then(({ ResidentProfileSettings }) => ({ default: ResidentProfileSettings })),
);

function RootRedirect() {
    const { isAuthenticated, isAuthReady, user } = useAuth();
    if (isAuthReady === false) {
        return <RouteLoadingFallback />;
    }
    if (!isAuthenticated) {
        return <Navigate to="/login" replace />;
    }
    if (user?.role === 'FIELD_OFFICIAL') {
        return <Navigate to="/field-official-mobile" replace />;
    }
    if (user?.role === 'RESIDENT') {
        return <Navigate to="/portal/documents" replace />;
    }
    return <Navigate to="/dashboard" replace />;
}

function FieldOfficialWebNotice() {
    const { isAuthenticated, user, logout } = useAuth();

    if (!isAuthenticated) return <Navigate to="/login" replace />;
    if (user?.role !== 'FIELD_OFFICIAL') return <Navigate to="/" replace />;

    return (
        <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6 py-12">
            <section className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
                <h1 className="text-2xl font-bold text-slate-900">Field operations are in the mobile app</h1>
                <p className="mt-3 text-sm leading-6 text-slate-600">
                    Field Official accounts do not have a web dashboard. Open KapitBayan on your mobile device to continue.
                </p>
                <button
                    type="button"
                    onClick={() => void logout()}
                    className="mt-6 inline-flex min-h-11 items-center justify-center rounded-lg bg-primary px-5 font-semibold text-primary-foreground outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
                >
                    Log out
                </button>
            </section>
        </main>
    );
}

export function App() {
    return (
        <ErrorBoundary>
            <AuthProvider>
                <Router>
                    <Suspense fallback={<RouteLoadingFallback />}>
                        <Routes>
                            {/* Root Intelligent Redirection */}
                            <Route path="/" element={<RootRedirect />} />

                            {/* Public Auth Routes */}
                            <Route path="/login" element={<Login />} />
                            <Route path="/field-official-mobile" element={<FieldOfficialWebNotice />} />
                            <Route path="/register" element={<Register />} />
                            <Route path="/register/official" element={<OfficialRegistration />} />
                            <Route path="/forgot-password" element={<ForgotPassword />} />
                            <Route path="/reset-password" element={<ResetPassword />} />
                            <Route path="/public/queue/:barangayId" element={<PublicQueueDisplay />} />
                            <Route path="/public/announcements/:barangayId" element={<PublicAnnouncements />} />
                            <Route path="/notice/:id" element={<PublicNoticeRedirect />} />

                            {/* Admin & Official Workstation (Tier 1 & Tier 2) */}
                            <Route element={<ProtectedRoute allowedRoles={['ADMIN', 'DILG_ADMIN']} />}>
                                <Route element={<AdminLayout />}>
                                    <Route path="/dashboard" element={<Dashboard />} />
                                    <Route path="/dilg-analytics" element={<DILGDashboard />} />
                                    <Route element={<ProtectedRoute allowedRoles={['DILG_ADMIN']} />}>
                                        <Route path="/dilg-applications" element={<BarangayApplications />} />
                                        <Route path="/dilg-accounts" element={<DILGAccountSupport />} />
                                    </Route>
                                    <Route path="/queue" element={<LiveQueue />} />
                                    <Route path="/documents" element={<DocumentRequests />} />
                                    <Route path="/settings" element={<Settings />} />
                                    <Route path="/barangay-settings" element={<BarangaySettings />} />
                                    <Route path="/notifications" element={<Notifications />} />
                                    <Route path="/faqs" element={<Faqs />} />
                                    <Route path="/communications" element={<Communications />} />
                                    <Route path="/residents" element={<ResidentsHub />} />
                                    <Route path="/verifications" element={<Navigate to="/residents?tab=verifications" replace />} />
                                    <Route path="/reports" element={<IssueReports />} />
                                    <Route element={<ProtectedRoute allowedRoles={['ADMIN']} />}>
                                        <Route path="/aid-requests" element={<AidRequests />} />
                                    </Route>
                                    <Route path="/profile" element={<AdminProfile />} />
                                </Route>
                            </Route>

                            {/* Citizen Desktop Portal (Tier 4: Residents & Self-Service Kiosks) */}
                            <Route element={<ProtectedRoute allowedRoles={['RESIDENT']} />}>
                                <Route element={<CitizenLayout />}>
                                    <Route path="/portal" element={<Navigate to="/portal/documents" replace />} />
                                    <Route path="/portal/documents" element={<CitizenDocuments />} />
                                    <Route path="/portal/queue" element={<CitizenQueue />} />
                                    <Route path="/portal/bulletin" element={<CitizenBulletin />} />
                                    <Route path="/portal/aid" element={<AidRequests />} />
                                    <Route path="/portal/help" element={<ResidentHelp />} />
                                    <Route path="/portal/tutorial" element={<ResidentTutorial />} />
                                    <Route path="/portal/profile" element={<ResidentProfileSettings />} />
                                </Route>
                            </Route>

                            {/* Fallback wildcard */}
                            <Route path="*" element={<RootRedirect />} />
                        </Routes>
                    </Suspense>
                </Router>
            </AuthProvider>
        </ErrorBoundary>
    );
}
