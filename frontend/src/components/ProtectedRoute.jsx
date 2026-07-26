import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

export default function ProtectedRoute({ children, adminOnly = false }) {
  const { user, loading } = useAuth();
  if (loading)
    return (
      <div className="min-h-[60vh] flex items-center justify-center text-stone" data-testid="route-loading">
        …
      </div>
    );
  if (!user) return <Navigate to="/login" replace />;
  const STAFF = ["admin", "manager", "marketing", "support", "accounting"];
  if (adminOnly && !STAFF.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}
