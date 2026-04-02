import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMermaid from "remark-mermaid-plugin";
import rehypeHighlight from "rehype-highlight";
import rehypeRaw from "rehype-raw";

interface ReadingViewProps {
  content: string;
}

// Optimization: ReadingView is a pure component that can be memoized
// to prevent unnecessary re-renders when the parent component updates
// but the `content` prop remains unchanged. This is especially
// important here because ReactMarkdown is a computationally expensive
// component to render.
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
