import React from 'react';
import ReactDOM from 'react-dom/client';
import {
  AlertCircle,
  Download,
  FileText,
  Loader2,
  Moon,
  RotateCcw,
  Sun,
  UploadCloud,
  Wand2,
} from 'lucide-react';
import './styles.css';

type ChapterInfo = {
  index: number;
  title: string;
};

type UploadAnalysis = {
  filename: string;
  extension: string;
  word_count: number;
  chapter_count: number;
  chapters: ChapterInfo[];
};

type BodyBlock =
  | { type: 'environment'; text: string }
  | { type: 'action'; character_id: string; character_name: string; text: string }
  | {
      type: 'performance';
      character_id: string;
      character_name: string;
      pre_action?: string;
      dialogue: string;
      post_action?: string;
    }
  | { type: 'transition'; text: string };

type ScriptScene = {
  index: number;
  source_chapter_index: number;
  title: string;
  camera_location: string;
  setting: string;
  time_of_day: string;
  body: BodyBlock[];
};

type ProgressState = {
  currentChapter: number;
  totalChapters: number;
  completedChapters: number;
  sceneCount: number;
  message: string;
};

type SSEMessage = {
  event: string;
  data: Record<string, unknown>;
};

const ACCEPTED_EXTENSIONS = ['.txt', '.docx', '.epub'];
const PREVIEW_LIMIT = 16000;
const CHARACTER_COLORS = [
  '#ff7a59',
  '#3ddc97',
  '#4cc9f0',
  '#f15bb5',
  '#fee440',
  '#9b5de5',
  '#00f5d4',
  '#ffb703',
  '#90be6d',
  '#f94144',
  '#577590',
  '#ff99c8',
];

function App() {
  const [file, setFile] = React.useState<File | null>(null);
  const [analysis, setAnalysis] = React.useState<UploadAnalysis | null>(null);
  const [yamlPreview, setYamlPreview] = React.useState('');
  const [finalYaml, setFinalYaml] = React.useState('');
  const [finalFountain, setFinalFountain] = React.useState('');
  const [scenes, setScenes] = React.useState<ScriptScene[]>([]);
  const [error, setError] = React.useState('');
  const [isDragging, setIsDragging] = React.useState(false);
  const [isAnalyzing, setIsAnalyzing] = React.useState(false);
  const [isConverting, setIsConverting] = React.useState(false);
  const [previewTheme, setPreviewTheme] = React.useState<'dark' | 'light'>('dark');
  const [progress, setProgress] = React.useState<ProgressState>({
    currentChapter: 0,
    totalChapters: 0,
    completedChapters: 0,
    sceneCount: 0,
    message: '',
  });
  const inputRef = React.useRef<HTMLInputElement | null>(null);
  const abortRef = React.useRef<AbortController | null>(null);

  async function acceptFile(nextFile: File) {
    setError('');
    setAnalysis(null);
    setYamlPreview('');
    setFinalYaml('');
    setFinalFountain('');
    setScenes([]);

    const localError = validateLocalFile(nextFile);
    if (localError) {
      setError(localError);
      setFile(null);
      return;
    }

    setFile(nextFile);
    setIsAnalyzing(true);
    try {
      const data = await uploadFile<UploadAnalysis>('/api/upload', nextFile);
      setAnalysis(data);
      setProgress({
        currentChapter: 0,
        totalChapters: data.chapter_count,
        completedChapters: 0,
        sceneCount: 0,
        message: '文件解析完成，可以开始转换。',
      });
    } catch (err) {
      setError(toErrorMessage(err));
      setFile(null);
    } finally {
      setIsAnalyzing(false);
    }
  }

  function resetUpload() {
    setFile(null);
    setAnalysis(null);
    setError('');
    setProgress({
      currentChapter: 0,
      totalChapters: 0,
      completedChapters: 0,
      sceneCount: scenes.length,
      message: '',
    });
    if (inputRef.current) inputRef.current.value = '';
  }

  async function convert() {
    if (!file || !analysis || analysis.chapter_count < 3) return;

    setError('');
    setYamlPreview('');
    setFinalYaml('');
    setFinalFountain('');
    setScenes([]);
    setIsConverting(true);
    setProgress({
      currentChapter: 0,
      totalChapters: analysis.chapter_count,
      completedChapters: 0,
      sceneCount: 0,
      message: '正在建立转换流。',
    });

    try {
      const controller = new AbortController();
      abortRef.current = controller;
      await streamConvert(file, controller.signal, (message) => handleStreamMessage(message, analysis));
    } catch (err) {
      if (!isAbortError(err)) {
        setError(toErrorMessage(err));
      }
    } finally {
      abortRef.current = null;
      setIsConverting(false);
    }
  }

  function stopConvert() {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsConverting(false);
    setProgress((current) => ({
      ...current,
      message: current.sceneCount > 0 ? '已停止生成，可继续查看当前结果。' : '已停止生成。',
    }));
  }

  function handleStreamMessage(message: SSEMessage, currentAnalysis: UploadAnalysis) {
    const { event, data } = message;

    if (event === 'progress') {
      setProgress((current) => ({
        ...current,
        completedChapters: toNumber(data.completed_chapters, current.completedChapters),
        totalChapters: toNumber(data.total_chapters, currentAnalysis.chapter_count),
        sceneCount: toNumber(data.scene_count, current.sceneCount),
        message: toStringValue(data.message, current.message),
      }));
      return;
    }

    if (event === 'chapter_started') {
      const chapterIndex = toNumber(data.chapter_index, 0);
      setProgress((current) => ({
        ...current,
        currentChapter: chapterIndex,
        totalChapters: toNumber(data.total_chapters, currentAnalysis.chapter_count),
        message: `正在处理第 ${chapterIndex} 章：${toStringValue(data.chapter_title, '')}`,
      }));
      return;
    }

    if (event === 'scene_completed') {
      const scene = normalizeScene(data.scene);
      const sceneYaml = toStringValue(data.scene_yaml, '');
      if (scene) {
        setScenes((current) => [...current, scene]);
      }
      if (sceneYaml) {
        setYamlPreview((current) => `${current}${current ? '\n' : ''}# Scene ${scene?.index ?? ''}\n${sceneYaml}`);
      }
      setProgress((current) => ({
        ...current,
        sceneCount: current.sceneCount + 1,
        message: `已生成第 ${scene?.index ?? current.sceneCount + 1} 场：${scene?.title ?? ''}`,
      }));
      return;
    }

    if (event === 'validation_result') {
      return;
    }

    if (event === 'final_yaml') {
      const yaml = toStringValue(data.yaml, '');
      const fountain = toStringValue(data.fountain, '');
      const sceneCount = toNumber(data.scene_count, scenes.length);
      setFinalYaml(yaml);
      setFinalFountain(fountain);
      setYamlPreview(yaml);
      setProgress((current) => ({
        ...current,
        completedChapters: current.totalChapters,
        sceneCount,
        message: '转换完成。',
      }));
      return;
    }

    if (event === 'error') {
      const detail = Array.isArray(data.errors)
        ? data.errors
            .map((item) => {
              if (typeof item === 'object' && item && 'location' in item && 'message' in item) {
                return `${String(item.location)}: ${String(item.message)}`;
              }
              return String(item);
            })
            .join('\n')
        : '';
      const errorMessage = toStringValue(data.message, '转换失败。');
      throw new Error(detail ? `${errorMessage}\n${detail}` : errorMessage);
    }
  }

  const novelTitle = getNovelTitle(analysis?.filename);
  const characterColorMap = React.useMemo(() => buildCharacterColorMap(scenes), [scenes]);

  return (
    <main className="app-shell">
      <section className="left-rail">
        <IntroPanel />

        <section className="upload-card">
          {!analysis ? (
            <UploadZone
              inputRef={inputRef}
              isDragging={isDragging}
              setIsDragging={setIsDragging}
              isAnalyzing={isAnalyzing}
              onFile={acceptFile}
            />
          ) : (
            <AnalysisCard
              analysis={analysis}
              progress={progress}
              isConverting={isConverting}
              onConvert={convert}
              onReset={resetUpload}
              onStop={stopConvert}
            />
          )}
        </section>

        {error && (
          <div className="notice error">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <OutputPanel
          title="ScreenYAML 预览"
          content={yamlPreview}
          fileName="plotweaver-script.yaml"
          downloadLabel="导出YAML"
          emptyText="生成后将在这里显示 ScreenYAML 片段。"
        />
      </section>

      <ScriptPreview
        title={novelTitle}
        scenes={scenes}
        characterColorMap={characterColorMap}
        theme={previewTheme}
        onToggleTheme={() => setPreviewTheme((current) => (current === 'dark' ? 'light' : 'dark'))}
        fallbackText={finalFountain}
        onDownload={() => downloadText(renderPlainScript(scenes, finalFountain), 'plotweaver-script.txt')}
        canDownload={scenes.length > 0 || Boolean(finalFountain)}
      />
    </main>
  );
}

function IntroPanel() {
  return (
    <section className="intro-panel">
      <h1 className="intro-title">
        <span className="title-brand">PlotWeaver</span>
        <span className="title-tagline">多章节小说剧本化的 AI 创作助手</span>
      </h1>
      <p>上传包含 3 章以上的 TXT、DOCX 或 EPUB 小说，按章节流式生成 ScreenYAML 剧本，并展示可导出的剧本预览。</p>
    </section>
  );
}

function UploadZone({
  inputRef,
  isDragging,
  setIsDragging,
  isAnalyzing,
  onFile,
}: {
  inputRef: React.RefObject<HTMLInputElement>;
  isDragging: boolean;
  setIsDragging: (value: boolean) => void;
  isAnalyzing: boolean;
  onFile: (file: File) => void | Promise<void>;
}) {
  return (
    <div
      className={`upload-zone ${isDragging ? 'is-dragging' : ''}`}
      onClick={() => inputRef.current?.click()}
      onDragOver={(event) => {
        event.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setIsDragging(false);
        const nextFile = event.dataTransfer.files[0];
        if (nextFile) void onFile(nextFile);
      }}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') inputRef.current?.click();
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".txt,.docx,.epub,.pdf"
        onChange={(event) => {
          const nextFile = event.target.files?.[0];
          if (nextFile) void onFile(nextFile);
        }}
      />
      {isAnalyzing ? <Loader2 className="spin" size={38} /> : <UploadCloud size={40} />}
      <strong>{isAnalyzing ? '正在解析文件' : '点击或拖拽上传小说'}</strong>
      <span>支持 TXT / DOCX / EPUB，PDF 暂不支持</span>
    </div>
  );
}

function AnalysisCard({
  analysis,
  progress,
  isConverting,
  onConvert,
  onReset,
  onStop,
}: {
  analysis: UploadAnalysis;
  progress: ProgressState;
  isConverting: boolean;
  onConvert: () => void;
  onReset: () => void;
  onStop: () => void;
}) {
  return (
    <div className="analysis-card">
      <header>
        <FileText size={17} />
        <strong>{analysis.filename}</strong>
      </header>
      <div className="analysis-grid">
        <Metric label="格式" value={analysis.extension.toUpperCase()} />
        <Metric label="字数" value={analysis.word_count.toLocaleString()} />
        <Metric label="章节" value={analysis.chapter_count.toString()} good={analysis.chapter_count >= 3} />
        <Metric label="场景" value={progress.sceneCount.toString()} good={progress.sceneCount > 0} />
      </div>
      <ChapterProgress progress={progress} totalFallback={analysis.chapter_count} />
      <div className="button-row">
        <button className="primary-button" onClick={() => void onConvert()} disabled={analysis.chapter_count < 3 || isConverting}>
          {isConverting ? <Loader2 className="spin" size={17} /> : <Wand2 size={17} />}
          生成结构化剧本
        </button>
        <button className="secondary-button" onClick={isConverting ? onStop : onReset}>
          {isConverting ? <AlertCircle size={16} /> : <RotateCcw size={16} />}
          {isConverting ? '停止生成' : '重新上传'}
        </button>
      </div>
    </div>
  );
}

function Metric({ label, value, good }: { label: string; value: string; good?: boolean }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong className={good ? 'good' : ''}>{value}</strong>
    </div>
  );
}

function ChapterProgress({ progress, totalFallback }: { progress: ProgressState; totalFallback: number }) {
  const total = progress.totalChapters || totalFallback;
  const completed = Math.min(progress.completedChapters, total);
  const percent = total > 0 ? Math.min(100, Math.round((completed / total) * 100)) : 0;
  return (
    <div className="chapter-progress" aria-label="章节转换进度">
      <div className="progress-topline">
        <span>{progress.message || '等待开始转换'}</span>
        <strong>
          {completed}/{total}
        </strong>
      </div>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

function OutputPanel({
  title,
  content,
  fileName,
  downloadLabel,
  emptyText,
}: {
  title: string;
  content: string;
  fileName: string;
  downloadLabel: string;
  emptyText: string;
}) {
  const isTruncated = content.length > PREVIEW_LIMIT;
  const previewContent = isTruncated
    ? `${content.slice(0, PREVIEW_LIMIT)}\n\n... 页面预览已截断，下载文件包含完整内容。`
    : content;
  return (
    <article className="yaml-panel">
      <header>
        <h2>{title}</h2>
        <button className="export-button" onClick={() => downloadText(content, fileName)} title={`下载 ${title}`} disabled={!content}>
          <Download size={17} />
          {downloadLabel}
        </button>
      </header>
      {content ? <pre>{previewContent}</pre> : <div className="yaml-empty">{emptyText}</div>}
    </article>
  );
}

function ScriptPreview({
  title,
  scenes,
  characterColorMap,
  theme,
  onToggleTheme,
  fallbackText,
  onDownload,
  canDownload,
}: {
  title: string;
  scenes: ScriptScene[];
  characterColorMap: Map<string, string>;
  theme: 'dark' | 'light';
  onToggleTheme: () => void;
  fallbackText: string;
  onDownload: () => void;
  canDownload: boolean;
}) {
  return (
    <section className={`script-preview ${theme === 'light' ? 'script-preview-light' : ''}`}>
      <header>
        <div>
          <p className="preview-label">剧本预览</p>
          <h2>{title}</h2>
        </div>
        <div className="preview-actions">
          <button className="theme-toggle" onClick={onToggleTheme}>
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            {theme === 'dark' ? '白底' : '黑底'}
          </button>
          <button className="preview-download" onClick={onDownload} disabled={!canDownload}>
            <Download size={17} />
            导出TXT
          </button>
        </div>
      </header>
      <div className="script-scroll">
        {scenes.length === 0 && !fallbackText && (
          <div className="preview-empty">
            <span>等待生成剧本</span>
            <p>右侧将随着章节转换逐场输出。</p>
          </div>
        )}
        {scenes.map((scene) => (
          <SceneView key={`${scene.source_chapter_index}-${scene.index}`} scene={scene} characterColorMap={characterColorMap} />
        ))}
        {scenes.length === 0 && fallbackText && <pre className="fallback-script">{fallbackText}</pre>}
      </div>
    </section>
  );
}

function SceneView({ scene, characterColorMap }: { scene: ScriptScene; characterColorMap: Map<string, string> }) {
  return (
    <article className="scene-view">
      <header>
        <strong>
          第 {scene.index} 场 （第 {scene.source_chapter_index} 章）
        </strong>
        <span>
          {scene.camera_location || '场景'} / {scene.setting} / {scene.time_of_day}
        </span>
      </header>
      <div className="scene-body">
        {scene.body.map((block, index) => (
          <BlockView block={block} key={index} characterColorMap={characterColorMap} />
        ))}
      </div>
    </article>
  );
}

function BlockView({ block, characterColorMap }: { block: BodyBlock; characterColorMap: Map<string, string> }) {
  if (block.type === 'environment') {
    return <p className="script-line script-line-small environment-line">（{block.text}）</p>;
  }

  if (block.type === 'transition') {
    return <p className="script-line script-line-small transition-line">{block.text}</p>;
  }

  if (block.type === 'action') {
    return (
      <p className="script-line">
        <CharacterName name={block.character_name} color={getMappedCharacterColor(block.character_name, characterColorMap)} />：
        <span className="action-text">（{block.text}）</span>
      </p>
    );
  }

  const pre = block.pre_action?.trim();
  const post = block.post_action?.trim();
  return (
    <p className="script-line">
      <CharacterName name={block.character_name} color={getMappedCharacterColor(block.character_name, characterColorMap)} />：
      {pre && <span className="action-text">（{pre}）</span>}
      <span className="dialogue-text">{block.dialogue}</span>
      {post && <span className="action-text">（{post}）</span>}
    </p>
  );
}

function CharacterName({ name, color }: { name: string; color: string }) {
  return (
    <span className="character-name" style={{ color }}>
      {name}
    </span>
  );
}

function validateLocalFile(nextFile: File): string {
  const lowerName = nextFile.name.toLowerCase();
  if (lowerName.endsWith('.pdf')) {
    return 'v1 暂不支持 PDF/OCR，请先将小说转换为 TXT、DOCX 或 EPUB 后再上传。';
  }
  if (!ACCEPTED_EXTENSIONS.some((ext) => lowerName.endsWith(ext))) {
    return '暂只支持 TXT、DOCX 和 EPUB 文件。';
  }
  if (nextFile.size > 8 * 1024 * 1024) {
    return '文件过大。v1 建议上传 8MB 以内的 TXT、DOCX 或 EPUB 小说。';
  }
  return '';
}

async function uploadFile<T>(path: string, file: File): Promise<T> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await fetch(path, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(String(data.detail || `请求失败: ${response.status}`));
  }
  return response.json() as Promise<T>;
}

async function streamConvert(file: File, signal: AbortSignal, onMessage: (message: SSEMessage) => void): Promise<void> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await fetch('/api/convert/stream', {
    method: 'POST',
    body: formData,
    signal,
  });
  if (!response.ok || !response.body) {
    const data = await response.json().catch(() => ({}));
    throw new Error(String(data.detail || `请求失败: ${response.status}`));
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split('\n\n');
    buffer = chunks.pop() ?? '';
    for (const chunk of chunks) {
      const parsed = parseSSEChunk(chunk);
      if (parsed) onMessage(parsed);
    }
  }

  if (buffer.trim()) {
    const parsed = parseSSEChunk(buffer);
    if (parsed) onMessage(parsed);
  }
}

function parseSSEChunk(chunk: string): SSEMessage | null {
  let event = 'message';
  const dataLines: string[] = [];

  for (const line of chunk.split('\n')) {
    if (line.startsWith('event:')) {
      event = line.slice('event:'.length).trim();
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice('data:'.length).trim());
    }
  }

  if (dataLines.length === 0) return null;
  return {
    event,
    data: JSON.parse(dataLines.join('\n')) as Record<string, unknown>,
  };
}

function normalizeScene(value: unknown): ScriptScene | null {
  if (!value || typeof value !== 'object') return null;
  const scene = value as Record<string, unknown>;
  const body = Array.isArray(scene.body) ? scene.body.filter(isBodyBlock) : [];
  return {
    index: toNumber(scene.index, 0),
    source_chapter_index: toNumber(scene.source_chapter_index, 0),
    title: toStringValue(scene.title, ''),
    camera_location: toStringValue(scene.camera_location, '场景'),
    setting: toStringValue(scene.setting, '未知地点'),
    time_of_day: toStringValue(scene.time_of_day, '未知'),
    body,
  };
}

function isBodyBlock(value: unknown): value is BodyBlock {
  if (!value || typeof value !== 'object') return false;
  const block = value as Record<string, unknown>;
  return typeof block.type === 'string';
}

function downloadText(content: string, fileName: string) {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
}

function renderPlainScript(scenes: ScriptScene[], fallbackText: string): string {
  if (scenes.length === 0) return fallbackText;
  return scenes
    .map((scene) => {
      const lines = [
        `第 ${scene.index} 场 （第 ${scene.source_chapter_index} 章）`,
        `${scene.camera_location || '场景'} / ${scene.setting} / ${scene.time_of_day}`,
        '',
        ...scene.body.map(renderPlainBlock),
      ];
      return lines.join('\n');
    })
    .join('\n\n');
}

function renderPlainBlock(block: BodyBlock): string {
  if (block.type === 'environment') return `（${block.text}）`;
  if (block.type === 'transition') return block.text;
  if (block.type === 'action') return `${block.character_name}：（${block.text}）`;
  const pre = block.pre_action?.trim() ? `（${block.pre_action.trim()}）` : '';
  const post = block.post_action?.trim() ? `（${block.post_action.trim()}）` : '';
  return `${block.character_name}：${pre}${block.dialogue}${post}`;
}

function getNovelTitle(filename?: string): string {
  if (!filename) return '未命名剧本';
  return filename.replace(/\.(txt|docx|epub)$/i, '');
}

function buildCharacterColorMap(scenes: ScriptScene[]): Map<string, string> {
  const map = new Map<string, string>();
  for (const scene of scenes) {
    for (const block of scene.body) {
      if ((block.type === 'action' || block.type === 'performance') && !map.has(block.character_name)) {
        map.set(block.character_name, CHARACTER_COLORS[map.size % CHARACTER_COLORS.length]);
      }
    }
  }
  return map;
}

function getMappedCharacterColor(name: string, colorMap: Map<string, string>): string {
  return colorMap.get(name) ?? CHARACTER_COLORS[0];
}

function toErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '发生未知错误。';
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}

function toNumber(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function toStringValue(value: unknown, fallback: string): string {
  return typeof value === 'string' ? value : fallback;
}

ReactDOM.createRoot(document.getElementById('root')!).render(<App />);
