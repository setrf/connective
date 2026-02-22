import { MessageSquare, Github, FileText } from "lucide-react";

const providerIcons: Record<string, React.ReactNode> = {
  slack: <MessageSquare className="h-4 w-4 text-purple-600" />,
  github: <Github className="h-4 w-4" />,
  google_drive: <FileText className="h-4 w-4 text-blue-600" />,
};

export function SourceIcon({ provider }: { provider: string }) {
  return providerIcons[provider] || <FileText className="h-4 w-4" />;
}
