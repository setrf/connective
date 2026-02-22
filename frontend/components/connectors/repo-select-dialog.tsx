"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiClient } from "@/lib/api-client";
import type { GitHubRepo } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface RepoSelectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (repos: string[]) => void;
  initialSelected?: string[];
}

export function RepoSelectDialog({
  open,
  onOpenChange,
  onConfirm,
  initialSelected = [],
}: RepoSelectDialogProps) {
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(
    new Set(initialSelected)
  );
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (open) {
      setLoading(true);
      setError(null);
      setSearch("");
      setSelected(new Set(initialSelected));
      apiClient
        .getGitHubRepos()
        .then((data: GitHubRepo[]) => setRepos(data))
        .catch(() => setError("Failed to load repositories"))
        .finally(() => setLoading(false));
    }
  }, [open, initialSelected]);

  const filtered = useMemo(() => {
    if (!search) return repos;
    const q = search.toLowerCase();
    return repos.filter(
      (r) =>
        r.full_name.toLowerCase().includes(q) ||
        (r.description && r.description.toLowerCase().includes(q))
    );
  }, [repos, search]);

  const toggle = useCallback((name: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }, []);

  const selectAll = useCallback(() => {
    setSelected(new Set(filtered.map((r) => r.full_name)));
  }, [filtered]);

  const deselectAll = useCallback(() => {
    setSelected(new Set());
  }, []);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Select GitHub Repositories</DialogTitle>
          <DialogDescription>
            Choose which repositories to sync. Only selected repos will be
            indexed.
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <p className="text-sm text-muted-foreground animate-pulse">
              Loading repositories...
            </p>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center py-12">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        ) : (
          <>
            <Input
              placeholder="Search repos..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />

            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={selectAll}>
                Select All
              </Button>
              <Button variant="ghost" size="sm" onClick={deselectAll}>
                Deselect All
              </Button>
              <span className="ml-auto text-xs text-muted-foreground">
                {selected.size} selected
              </span>
            </div>

            <div className="flex-1 overflow-y-auto min-h-0 max-h-[40vh] border rounded-md divide-y">
              {filtered.length === 0 ? (
                <p className="text-sm text-muted-foreground p-4 text-center">
                  No repos found
                </p>
              ) : (
                filtered.map((repo) => (
                  <label
                    key={repo.full_name}
                    className="flex items-start gap-3 p-3 hover:bg-muted/50 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selected.has(repo.full_name)}
                      onChange={() => toggle(repo.full_name)}
                      className="mt-1 h-4 w-4 rounded border-input"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium truncate">
                          {repo.full_name}
                        </span>
                        {repo.private && (
                          <Badge variant="secondary" className="text-xs shrink-0">
                            private
                          </Badge>
                        )}
                      </div>
                      {repo.description && (
                        <p className="text-xs text-muted-foreground truncate mt-0.5">
                          {repo.description}
                        </p>
                      )}
                      <div className="flex items-center gap-3 mt-1">
                        {repo.language && (
                          <span className="text-xs text-muted-foreground">
                            {repo.language}
                          </span>
                        )}
                        {repo.stargazers_count > 0 && (
                          <span className="text-xs text-muted-foreground">
                            ★ {repo.stargazers_count}
                          </span>
                        )}
                      </div>
                    </div>
                  </label>
                ))
              )}
            </div>
          </>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={selected.size === 0 || loading}
            onClick={() => onConfirm(Array.from(selected))}
          >
            Confirm ({selected.size})
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
