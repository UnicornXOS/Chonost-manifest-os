import { memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMermaid from "remark-mermaid-plugin";
import rehypeHighlight from "rehype-highlight";
import rehypeRaw from "rehype-raw";

interface ReadingViewProps {
  content: string;
}

// By wrapping ReadingView with React.memo, we prevent it from re-rendering
// if its props (in this case, `content`) have not changed. This is a
// significant performance optimization for a component that might be
// part of a larger, frequently updating parent component.
function ReadingView({ content }: ReadingViewProps) {

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
}

export default memo(ReadingView);
