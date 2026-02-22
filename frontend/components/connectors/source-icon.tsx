import { MessageSquare, Github, FileText } from "lucide-react";

const icons: Record<string, React.ReactNode> = {
  slack: <MessageSquare className="h-5 w-5" />,
  github: <Github className="h-5 w-5" />,
  google_drive: <FileText className="h-5 w-5" />,
};

const labels: Record<string, string> = {
  slack: "Slack",
  github: "GitHub",
  google_drive: "Google Drive",
};

export function SourceIcon({ provider }: { provider: string }) {
  return (
    <div className="flex items-center gap-2">
      {icons[provider] || <FileText className="h-5 w-5" />}
      <span className="font-medium">{labels[provider] || provider}</span>
    </div>
  );
}
