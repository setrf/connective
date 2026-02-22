"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiClient } from "@/lib/api-client";
import type { GoogleDriveFolder } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface FolderSelectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (folders: GoogleDriveFolder[]) => void;
  initialSelected?: GoogleDriveFolder[];
}

export function FolderSelectDialog({
  open,
  onOpenChange,
  onConfirm,
  initialSelected = [],
}: FolderSelectDialogProps) {
  const [folders, setFolders] = useState<GoogleDriveFolder[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(
    new Set(initialSelected.map((f) => f.id))
  );
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (open) {
      setLoading(true);
      setError(null);
      setSearch("");
      setSelected(new Set(initialSelected.map((f) => f.id)));
      apiClient
        .getGoogleDriveFolders()
        .then((data: GoogleDriveFolder[]) => setFolders(data))
        .catch(() => setError("Failed to load folders"))
        .finally(() => setLoading(false));
    }
  }, [open, initialSelected]);

  const filtered = useMemo(() => {
    if (!search) return folders;
    const q = search.toLowerCase();
    return folders.filter((f) => f.name.toLowerCase().includes(q));
  }, [folders, search]);

  const toggle = useCallback((id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const selectAll = useCallback(() => {
    setSelected(new Set(filtered.map((f) => f.id)));
  }, [filtered]);

  const deselectAll = useCallback(() => {
    setSelected(new Set());
  }, []);

  const handleConfirm = useCallback(() => {
    const selectedFolders = folders.filter((f) => selected.has(f.id));
    onConfirm(selectedFolders);
  }, [folders, selected, onConfirm]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Select Google Drive Folders</DialogTitle>
          <DialogDescription>
            Choose which folders to sync. Files in subfolders are included
            recursively.
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <p className="text-sm text-muted-foreground animate-pulse">
              Loading folders...
            </p>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center py-12">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        ) : (
          <>
            <Input
              placeholder="Search folders..."
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
                  No folders found
                </p>
              ) : (
                filtered.map((folder) => (
                  <label
                    key={folder.id}
                    className="flex items-center gap-3 p-3 hover:bg-muted/50 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selected.has(folder.id)}
                      onChange={() => toggle(folder.id)}
                      className="h-4 w-4 rounded border-input"
                    />
                    <span className="text-sm font-medium truncate">
                      {folder.name}
                    </span>
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
            onClick={handleConfirm}
          >
            Confirm ({selected.size})
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
