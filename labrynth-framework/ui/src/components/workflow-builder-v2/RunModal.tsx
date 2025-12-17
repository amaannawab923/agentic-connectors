import React, { useState } from "react";
import {
  X,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Send,
  User,
} from "lucide-react";

interface RunStep {
  id: string;
  name: string;
  status: "success" | "error" | "running" | "pending";
  duration: number;
  startTime: string;
  endTime?: string;
  error?: string;
}

interface Comment {
  id: string;
  author: string;
  text: string;
  timestamp: string;
}

interface Run {
  id: string;
  status: "success" | "error" | "running" | "pending";
  startTime: string;
  endTime?: string;
  duration: number;
  triggeredBy: string;
  steps: RunStep[];
  comments: Comment[];
}

interface RunModalProps {
  run: Run;
  isDark: boolean;
  onClose: () => void;
}

export function RunModal({ run, isDark, onClose }: RunModalProps) {
  const [comments, setComments] = useState<Comment[]>(run.comments);
  const [newComment, setNewComment] = useState("");

  const handleAddComment = () => {
    if (!newComment.trim()) return;

    const comment: Comment = {
      id: `comment-${Date.now()}`,
      author: "Anonymous User",
      text: newComment,
      timestamp: new Date().toISOString(),
    };

    setComments([...comments, comment]);
    setNewComment("");
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "success":
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case "error":
        return <XCircle className="w-4 h-4 text-red-500" />;
      case "running":
        return <Clock className="w-4 h-4 text-blue-500 animate-spin" />;
      case "pending":
        return <AlertCircle className="w-4 h-4 text-gray-400" />;
      default:
        return null;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "success":
        return "text-green-500";
      case "error":
        return "text-red-500";
      case "running":
        return "text-blue-500";
      case "pending":
        return "text-gray-400";
      default:
        return "text-gray-400";
    }
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
  };

  const formatTimestamp = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div
      className="fixed inset-0 backdrop-blur-sm flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className={`${isDark ? "bg-[#1a1a1a] border-gray-700" : "bg-white border-gray-300"} border rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className={`px-6 py-4 ${isDark ? "border-gray-700" : "border-gray-300"} border-b flex items-center justify-between`}
        >
          <div>
            <div className="flex items-center gap-3">
              <h2
                className={`text-lg font-semibold ${isDark ? "text-gray-200" : "text-gray-900"}`}
              >
                Run #{run.id}
              </h2>
              <div className="flex items-center gap-2">
                {getStatusIcon(run.status)}
                <span
                  className={`text-sm font-medium ${getStatusColor(run.status)}`}
                >
                  {run.status.charAt(0).toUpperCase() + run.status.slice(1)}
                </span>
              </div>
            </div>
            <div
              className={`text-sm ${isDark ? "text-gray-400" : "text-gray-600"} mt-1`}
            >
              Started {formatTimestamp(run.startTime)} • Triggered by{" "}
              {run.triggeredBy}
            </div>
          </div>
          <button
            onClick={onClose}
            className={`p-2 ${isDark ? "hover:bg-[#2a2a2a]" : "hover:bg-gray-100"} rounded`}
          >
            <X
              className={`w-5 h-5 ${isDark ? "text-gray-400" : "text-gray-600"}`}
            />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto">
          {/* Run Summary */}
          <div
            className={`px-6 py-4 ${isDark ? "border-gray-700" : "border-gray-300"} border-b`}
          >
            <h3
              className={`text-sm font-medium ${isDark ? "text-gray-300" : "text-gray-700"} mb-3`}
            >
              Summary
            </h3>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <div
                  className={`text-xs ${isDark ? "text-gray-500" : "text-gray-400"} mb-1`}
                >
                  Duration
                </div>
                <div
                  className={`text-sm font-medium ${isDark ? "text-gray-200" : "text-gray-900"}`}
                >
                  {formatDuration(run.duration)}
                </div>
              </div>
              <div>
                <div
                  className={`text-xs ${isDark ? "text-gray-500" : "text-gray-400"} mb-1`}
                >
                  Steps
                </div>
                <div
                  className={`text-sm font-medium ${isDark ? "text-gray-200" : "text-gray-900"}`}
                >
                  {run.steps.length}
                </div>
              </div>
              <div>
                <div
                  className={`text-xs ${isDark ? "text-gray-500" : "text-gray-400"} mb-1`}
                >
                  Status
                </div>
                <div
                  className={`text-sm font-medium ${getStatusColor(run.status)}`}
                >
                  {run.status.charAt(0).toUpperCase() + run.status.slice(1)}
                </div>
              </div>
            </div>
          </div>

          {/* Steps */}
          <div
            className={`px-6 py-4 ${isDark ? "border-gray-700" : "border-gray-300"} border-b`}
          >
            <h3
              className={`text-sm font-medium ${isDark ? "text-gray-300" : "text-gray-700"} mb-3`}
            >
              Steps
            </h3>
            <div className="space-y-3">
              {run.steps.map((step, index) => (
                <div
                  key={step.id}
                  className={`${isDark ? "bg-[#0a0a0a]" : "bg-gray-50"} rounded-lg p-3`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-xs ${isDark ? "text-gray-500" : "text-gray-400"}`}
                      >
                        Step {index + 1}
                      </span>
                      <span
                        className={`text-sm font-medium ${isDark ? "text-gray-200" : "text-gray-900"}`}
                      >
                        {step.name}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      {getStatusIcon(step.status)}
                      <span
                        className={`text-xs ${isDark ? "text-gray-400" : "text-gray-600"}`}
                      >
                        {formatDuration(step.duration)}
                      </span>
                    </div>
                  </div>
                  {step.error && (
                    <div
                      className={`text-xs ${isDark ? "text-red-400" : "text-red-600"} mt-2`}
                    >
                      Error: {step.error}
                    </div>
                  )}
                  <div
                    className={`text-xs ${isDark ? "text-gray-500" : "text-gray-400"} mt-1`}
                  >
                    {formatTimestamp(step.startTime)}
                    {step.endTime && ` - ${formatTimestamp(step.endTime)}`}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Comments */}
          <div className="px-6 py-4">
            <h3
              className={`text-sm font-medium ${isDark ? "text-gray-300" : "text-gray-700"} mb-3`}
            >
              Comments ({comments.length})
            </h3>

            {/* Comments List */}
            <div className="space-y-3 mb-4">
              {comments.length === 0 ? (
                <div
                  className={`text-sm ${isDark ? "text-gray-500" : "text-gray-400"} text-center py-4`}
                >
                  No comments yet. Be the first to comment!
                </div>
              ) : (
                comments.map((comment) => (
                  <div
                    key={comment.id}
                    className={`${isDark ? "bg-[#0a0a0a]" : "bg-gray-50"} rounded-lg p-3`}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <div
                        className={`w-6 h-6 rounded-full ${isDark ? "bg-[#2a2a2a]" : "bg-gray-200"} flex items-center justify-center`}
                      >
                        <User
                          className={`w-3 h-3 ${isDark ? "text-gray-400" : "text-gray-600"}`}
                        />
                      </div>
                      <span
                        className={`text-sm font-medium ${isDark ? "text-gray-300" : "text-gray-700"}`}
                      >
                        {comment.author}
                      </span>
                      <span
                        className={`text-xs ${isDark ? "text-gray-500" : "text-gray-400"}`}
                      >
                        {formatTimestamp(comment.timestamp)}
                      </span>
                    </div>
                    <p
                      className={`text-sm ${isDark ? "text-gray-400" : "text-gray-600"}`}
                    >
                      {comment.text}
                    </p>
                  </div>
                ))
              )}
            </div>

            {/* Add Comment */}
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Add a comment..."
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === "Enter") {
                    handleAddComment();
                  }
                }}
                className={`flex-1 ${isDark ? "bg-[#0a0a0a] border-gray-700 text-gray-300 placeholder-gray-600" : "bg-white border-gray-300 text-gray-900 placeholder-gray-400"} border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500`}
              />
              <button
                onClick={handleAddComment}
                disabled={!newComment.trim()}
                className={`px-4 py-2 rounded-lg text-sm font-medium ${
                  newComment.trim()
                    ? "bg-blue-600 hover:bg-blue-700 text-white"
                    : isDark
                      ? "bg-[#2a2a2a] text-gray-600 cursor-not-allowed"
                      : "bg-gray-100 text-gray-400 cursor-not-allowed"
                }`}
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}