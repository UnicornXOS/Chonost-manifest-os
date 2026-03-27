import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMermaid from "remark-mermaid-plugin";
import rehypeHighlight from "rehype-highlight";
import rehypeRaw from "rehype-raw";

interface ReadingViewProps {
  content: string;
}

// ReadingView is a performance-critical component that re-renders frequently.
// It uses ReactMarkdown with multiple plugins, which can be computationally expensive.
// Wrapping it in React.memo prevents unnecessary re-renders when the `content` prop is unchanged,
// significantly improving performance in scenarios where the parent component re-renders
// but the content for this view has not changed.
const ReadingView = React.memo(function ReadingView({ content }: ReadingViewProps) {
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
