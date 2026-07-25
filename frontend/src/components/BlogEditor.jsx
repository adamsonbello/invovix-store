import React, { useRef, useMemo, useState, useCallback } from "react";
import ReactQuill from "react-quill-new";
import "react-quill-new/dist/quill.snow.css";
import { X, Upload } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { useI18n } from "@/i18n";

export default function BlogEditor({ post, onSaved, onCancel }) {
  const { t } = useI18n();
  const quillRef = useRef(null);
  const [form, setForm] = useState({
    title: post?.title || "",
    excerpt: post?.excerpt || "",
    content: post?.content || "",
    cover_image: post?.cover_image || "",
    tags: (post?.tags || []).join(", "),
    published: post?.published ?? true,
  });
  const [saving, setSaving] = useState(false);

  const uploadFile = async (file) => {
    const fd = new FormData();
    fd.append("file", file);
    const res = await api.post("/admin/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
    return res.data.url;
  };

  const imageHandler = useCallback(() => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.click();
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;
      try {
        const url = await uploadFile(file);
        const editor = quillRef.current.getEditor();
        const range = editor.getSelection(true);
        editor.insertEmbed(range.index, "image", url);
        editor.setSelection(range.index + 1);
      } catch (e) {
        toast.error(formatApiError(e.response?.data?.detail));
      }
    };
  }, []);

  const modules = useMemo(
    () => ({
      toolbar: {
        container: [
          [{ header: [2, 3, 4, false] }],
          ["bold", "italic", "underline", "strike", "blockquote"],
          [{ list: "ordered" }, { list: "bullet" }],
          [{ align: [] }],
          ["link", "image"],
          [{ color: [] }, { background: [] }],
          ["clean"],
        ],
        handlers: { image: imageHandler },
      },
    }),
    [imageHandler]
  );

  const uploadCover = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const url = await uploadFile(file);
      setForm((f) => ({ ...f, cover_image: url }));
      toast.success("OK");
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    }
  };

  const save = async () => {
    if (!form.title.trim()) return toast.error(t.admin.postTitle);
    setSaving(true);
    const payload = {
      title: form.title,
      excerpt: form.excerpt,
      content: form.content,
      cover_image: form.cover_image,
      tags: form.tags.split(",").map((s) => s.trim()).filter(Boolean),
      published: form.published,
    };
    try {
      if (post) await api.put(`/admin/blog/${post.id}`, payload);
      else await api.post("/admin/blog", payload);
      toast.success("OK");
      onSaved();
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-ink/50 flex items-start justify-center overflow-auto p-4" data-testid="blog-editor">
      <div className="bg-cream w-full max-w-4xl my-8 p-8" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-6">
          <h3 className="font-display font-bold text-2xl">{post ? t.admin.editPost : t.admin.newPost}</h3>
          <button onClick={onCancel} data-testid="blog-editor-close"><X className="w-6 h-6" /></button>
        </div>

        <div className="space-y-5">
          <div>
            <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{t.admin.postTitle}</label>
            <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none focus:border-ink text-xl font-display font-bold" data-testid="blog-title" />
          </div>

          <div>
            <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{t.admin.excerpt}</label>
            <textarea value={form.excerpt} onChange={(e) => setForm({ ...form, excerpt: e.target.value })} rows={2} className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none focus:border-ink" data-testid="blog-excerpt" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{t.admin.coverImage}</label>
              <div className="flex gap-2">
                <input value={form.cover_image} onChange={(e) => setForm({ ...form, cover_image: e.target.value })} className="flex-1 px-4 py-3 border border-ink/20 bg-transparent outline-none focus:border-ink" data-testid="blog-cover" />
                <label className="shrink-0 inline-flex items-center gap-2 border border-ink px-4 cursor-pointer hover:bg-ink hover:text-cream transition-colors" data-testid="blog-cover-upload">
                  <Upload className="w-4 h-4" /> {t.admin.uploadCover}
                  <input type="file" accept="image/*" className="hidden" onChange={uploadCover} />
                </label>
              </div>
              {form.cover_image && <img src={form.cover_image} alt="cover" className="mt-3 h-28 w-full object-cover bg-[#f0efed]" />}
            </div>
            <div>
              <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{t.admin.tags}</label>
              <input value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} placeholder="Domotique, Télétravail" className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none focus:border-ink" data-testid="blog-tags" />
              <label className="flex items-center gap-2 mt-4 font-medium">
                <input type="checkbox" checked={form.published} onChange={(e) => setForm({ ...form, published: e.target.checked })} className="accent-brand w-4 h-4" data-testid="blog-published" />
                {t.admin.published}
              </label>
            </div>
          </div>

          <div>
            <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{t.admin.content}</label>
            <div className="bg-white border border-ink/20">
              <ReactQuill ref={quillRef} theme="snow" value={form.content} onChange={(v) => setForm({ ...form, content: v })} modules={modules} placeholder={t.admin.writeContent} />
            </div>
          </div>

          <button onClick={save} disabled={saving} className="w-full bg-brand text-white py-4 rounded-full font-medium hover:bg-ink transition-colors disabled:opacity-50" data-testid="blog-save">
            {saving ? t.common.loading : t.admin.savePost}
          </button>
        </div>
      </div>
    </div>
  );
}
