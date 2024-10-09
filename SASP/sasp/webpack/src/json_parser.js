import $ from 'jquery';
import { createRoot } from 'react-dom/client';
import ReactJson from '@microlink/react-json-view'

$(function() {
    $('.json-field').each(function() {
        try {
            const json = JSON.parse($(this).text());
            const root = createRoot(this);
            root.render(<ReactJson src={json} name={false}/>);
        } catch (error) {
            console.error(error);
        }
    });
});