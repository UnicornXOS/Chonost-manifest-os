import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMermaid from "remark-mermaid-plugin";
import rehypeHighlight from "rehype-highlight";
import rehypeRaw from "rehype-raw";

interface ReadingViewProps {
  content: string;
}

// ReadingView is a performance-sensitive component that renders markdown.
// It is wrapped in React.memo to prevent unnecessary re-renders when the parent
// component's state changes, but the `content` prop remains the same.
// This avoids expensive markdown processing on every render.
const ReadingView = React.memo(({ content }: ReadingViewProps) => {
  return (
    <div className="reading">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMermaid as any]}
        rehypePlugins={[rehypeHighlight, rehypeRaw]}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
});

export default ReadingView;
